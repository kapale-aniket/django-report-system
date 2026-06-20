"""End-to-end flow tests and user-friendly message checks."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from api.tests.base import APITestBase, dummy_pdf
from apps.reports.infrastructure.models import Report
from core.utils.user_messages import looks_technical

User = get_user_model()


def assert_user_friendly(test_case, message: str, *, label: str = '') -> None:
    prefix = f'{label}: ' if label else ''
    test_case.assertTrue(message, f'{prefix}message must not be empty')
    test_case.assertFalse(
        looks_technical(message),
        f'{prefix}technical message shown to user: {message!r}',
    )
    test_case.assertNotIn('Traceback', message)
    test_case.assertNotIn('Unexpected service error', message)


class EndToEndApprovalFlowTests(APITestBase):
    """Student submit → teacher final approve → admin approve → certificate + celebration."""

    def test_full_individual_approval_certificate_celebration_flow(self):
        student_token = self.login(self.student.username)
        self.auth(student_token)
        submit = self.client.post(
            reverse('reports_api:submit'),
            {
                'title': 'E2E Individual Project',
                'file': dummy_pdf('e2e_individual.pdf'),
                'academic_year': '2025-2026',
            },
            format='multipart',
        )
        self.assert_api_success(submit, 'student submit')
        report = Report.objects.get(title='E2E Individual Project')

        teacher_token = self.login(self.teacher.username)
        self.auth(teacher_token)
        teacher_resp = self.client.post(
            reverse('reports_api:teacher_approve', kwargs={'pk': report.pk}),
            {
                'marks': 88,
                'feedback': 'Strong work.',
                'is_final_submission': True,
            },
            format='json',
        )
        self.assert_api_success(teacher_resp, 'teacher approve final')
        report.refresh_from_db()
        self.assertTrue(report.teacher_approved)
        self.assertTrue(report.is_final_submission)

        admin_token = self.login(self.admin.username)
        self.auth(admin_token)
        admin_resp = self.client.post(
            reverse('reports_api:admin_approve', kwargs={'pk': report.pk}),
            {'marks': 90, 'feedback': 'Approved.'},
            format='json',
        )
        self.assert_api_success(admin_resp, 'admin approve')
        report.refresh_from_db()
        self.assertTrue(report.admin_approved)
        self.assertTrue(report.certificate_generated)

        student_token = self.login(self.student.username)
        self.auth(student_token)
        cert_resp = self.client.get(reverse('reports_api:certificate', kwargs={'pk': report.pk}))
        self.assertEqual(cert_resp.status_code, 200)
        self.assertEqual(cert_resp['Content-Type'], 'application/pdf')

        session_client = Client()
        session_client.force_login(self.student)
        dashboard = session_client.get(reverse('dashboard:student_dashboard'))
        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, 'certCelebrationRoot')
        self.assertContains(dashboard, 'E2E Individual Project')

        ack = session_client.post(reverse('reports:certificate_celebration_ack', kwargs={'pk': report.pk}))
        self.assertEqual(ack.status_code, 200)
        self.assertTrue(ack.json()['success'])
        dashboard_after = session_client.get(reverse('dashboard:student_dashboard'))
        self.assertNotContains(dashboard_after, 'certCelebrationRoot')

    def test_full_group_flow_member_profiles_and_certificates(self):
        mate = User.objects.create_user(
            username='e2e_mate',
            password=self.password,
            email='e2e_mate@test.com',
            role=User.Role.STUDENT,
            department=self.department_name,
            is_active=True,
            first_name='Group',
            last_name='Mate',
        )
        group = self.create_project_group(mate=mate, name='E2E Group Project')
        submitter_token = self.login(self.student.username)
        submit = self.submit_group_report(
            token=submitter_token,
            group=group,
            title='E2E Group Report',
        )
        self.assert_api_success(submit, 'group submit')
        report = Report.objects.get(title='E2E Group Report')

        teacher_token = self.login(self.teacher.username)
        self.auth(teacher_token)
        self.client.post(
            reverse('reports_api:teacher_approve', kwargs={'pk': report.pk}),
            {'marks': 85, 'feedback': 'Good teamwork.', 'is_final_submission': True},
            format='json',
        )

        admin_token = self.login(self.admin.username)
        self.auth(admin_token)
        admin_resp = self.client.post(
            reverse('reports_api:admin_approve', kwargs={'pk': report.pk}),
            {'marks': 87},
            format='json',
        )
        self.assert_api_success(admin_resp, 'group admin approve')
        report.refresh_from_db()
        member_codes = report.certificate_member_codes_json or {}
        self.assertTrue(report.certificate_verification_code)
        self.assertIn(str(mate.pk), member_codes)

        session_client = Client()
        session_client.force_login(self.student)
        profiles = session_client.get(
            reverse('reports:group_member_profiles', kwargs={'pk': report.pk})
        )
        self.assertEqual(profiles.status_code, 200)
        self.assertContains(profiles, self.student.get_full_name() or self.student.username)
        self.assertContains(profiles, mate.get_full_name() or mate.username)

        groups_page = session_client.get(reverse('reports:project_groups'))
        self.assertEqual(groups_page.status_code, 200)
        self.assertContains(groups_page, 'E2E Group Project')
        self.assertContains(groups_page, mate.first_name)


class UserFriendlyMessageTests(APITestBase):
    def test_login_invalid_credentials_message(self):
        response = self.client.post(
            reverse('accounts_api:login'),
            {'username': self.student.username, 'password': 'wrong-password'},
            format='json',
        )
        self.assertFalse(response.data['success'])
        assert_user_friendly(self, response.data['message'], label='login invalid')

    def test_unauthenticated_api_message(self):
        response = self.client.get(reverse('reports_api:my_reports'))
        self.assertFalse(response.data['success'])
        assert_user_friendly(self, response.data['message'], label='unauthenticated')
        self.assertEqual(response.data['message'], 'Please sign in to continue.')

    def test_permission_denied_message(self):
        token = self.login(self.student.username)
        self.auth(token)
        report = self.create_report()
        response = self.client.post(
            reverse('reports_api:admin_approve', kwargs={'pk': report.pk}),
            {'marks': 90},
            format='json',
        )
        self.assertFalse(response.data['success'])
        assert_user_friendly(self, response.data['message'], label='permission denied')

    def test_certificate_analyze_without_image(self):
        session_client = Client()
        session_client.force_login(self.admin)
        response = session_client.post(reverse('reports:certificate_template_analyze'))
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertFalse(payload['success'])
        assert_user_friendly(self, payload['message'], label='certificate analyze')

    def test_certificate_download_unavailable_message(self):
        report = self.create_report(title='No Cert Yet')
        session_client = Client()
        session_client.force_login(self.student)
        from django.contrib.messages import get_messages

        response = session_client.get(reverse('reports:certificate', kwargs={'pk': report.pk}), follow=True)
        flash = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(flash)
        assert_user_friendly(self, flash[0], label='certificate unavailable')
