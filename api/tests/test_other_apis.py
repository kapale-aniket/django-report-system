"""Integration tests for messaging, Q&A, dashboard, and certificate APIs."""
from django.urls import reverse

from api.tests.base import APITestBase
from apps.reports.infrastructure.models import Report


class MessagingAPITests(APITestBase):
    def test_compose_inbox_sent_read_reply(self):
        student_token = self.login(self.student.username)
        teacher_token = self.login(self.teacher.username)

        self.auth(student_token)
        compose = self.client.post(
            reverse('messaging_api:compose'),
            {'receiver_id': self.teacher.pk, 'body': 'Question about my report.'},
            format='json',
        )
        self.assert_api_success(compose, 'compose')
        message_id = compose.data['data']['id']

        inbox = self.client.get(reverse('messaging_api:inbox'))
        self.assert_api_success(inbox, 'student inbox')

        sent = self.client.get(reverse('messaging_api:sent'))
        self.assert_api_success(sent, 'sent')

        self.auth(teacher_token)
        teacher_inbox = self.client.get(reverse('messaging_api:inbox'))
        self.assert_api_success(teacher_inbox, 'teacher inbox')

        read = self.client.post(reverse('messaging_api:mark_read', kwargs={'message_id': message_id}))
        self.assert_api_success(read, 'mark read')

        reply = self.client.post(
            reverse('messaging_api:reply', kwargs={'message_id': message_id}),
            {'body': 'Please check the rubric.'},
            format='json',
        )
        self.assert_api_success(reply, 'reply')


class QAAPITests(APITestBase):
    def test_faq_list_and_ask(self):
        token = self.login(self.student.username)
        self.auth(token)

        faqs = self.client.get(reverse('qa_api:faq_list'))
        self.assert_api_success(faqs, 'faq list')

        ask = self.client.post(
            reverse('qa_api:ask'),
            {'subject': 'Upload issue', 'body': 'My PDF fails validation.'},
            format='json',
        )
        self.assert_api_success(ask, 'ask')

        questions = self.client.get(reverse('qa_api:question_list'))
        self.assert_api_success(questions, 'question list')

    def test_visitor_ask(self):
        response = self.client.post(
            reverse('qa_api:visitor_ask'),
            {
                'name': 'Guest',
                'email': 'guest@example.com',
                'subject': 'Public question',
                'body': 'How does verification work?',
            },
            format='json',
        )
        self.assert_api_success(response, 'visitor ask')

    def test_admin_reply_and_ai_suggest(self):
        user_question = self.create_user_question()
        visitor_question = self.create_visitor_question()
        admin_token = self.login(self.admin.username)
        self.auth(admin_token)

        user_reply = self.client.post(
            reverse('qa_api:reply', kwargs={'question_id': user_question.pk}),
            {'answer_text': 'Upload a PDF under the size limit.'},
            format='json',
        )
        self.assert_api_success(user_reply, 'user reply')

        visitor_reply = self.client.post(
            reverse('qa_api:visitor_reply', kwargs={'question_id': visitor_question.pk}),
            {'answer_text': 'Scan the QR code on the certificate.'},
            format='json',
        )
        self.assert_api_success(visitor_reply, 'visitor reply')

        suggest = self.client.post(
            reverse('qa_api:suggest_reply'),
            {'question_id': user_question.pk, 'question_type': 'user'},
            format='json',
        )
        self.assert_api_success(suggest, 'suggest reply')
        self.assertIn('suggested_answer', suggest.data['data'])


class DashboardAPITests(APITestBase):
    def test_role_dashboards(self):
        self.create_report()
        admin_token = self.login(self.admin.username)
        teacher_token = self.login(self.teacher.username)
        student_token = self.login(self.student.username)

        self.auth(admin_token)
        admin = self.client.get(reverse('dashboard_api:admin_analytics'))
        self.assert_api_success(admin, 'admin dashboard')

        self.auth(teacher_token)
        teacher = self.client.get(reverse('dashboard_api:teacher_dashboard'))
        self.assert_api_success(teacher, 'teacher dashboard')

        self.auth(student_token)
        student = self.client.get(reverse('dashboard_api:student_dashboard'))
        self.assert_api_success(student, 'student dashboard')


class CertificateAPITests(APITestBase):
    def test_verify_valid_and_invalid_code(self):
        report = self.create_report(
            title='Verified Report',
            status=Report.Status.APPROVED,
            teacher_approved=True,
            admin_approved=True,
            is_final_submission=True,
            marks=95,
        )
        report.certificate_verification_code = 'valid-test-code-xyz'
        report.save(update_fields=['certificate_verification_code'])

        valid = self.client.get(
            reverse('certificates_api:verify'),
            {'code': 'valid-test-code-xyz'},
        )
        self.assert_api_success(valid, 'certificate verify valid')

        invalid = self.client.get(
            reverse('certificates_api:verify'),
            {'code': 'does-not-exist'},
        )
        self.assertFalse(invalid.data['success'])
