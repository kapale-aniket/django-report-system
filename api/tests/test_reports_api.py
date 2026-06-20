"""Integration tests for /api/v1/reports/* endpoints."""
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.urls import reverse

from api.tests.base import APITestBase, dummy_docx, dummy_pdf
from apps.reports.infrastructure.models import Notification, Report

User = get_user_model()


class ReportListSubmitAPITests(APITestBase):
    def test_report_list(self):
        self.create_report()
        token = self.login(self.admin.username)
        self.auth(token)
        response = self.client.get(reverse('reports_api:report_list'))
        self.assert_api_success(response, 'report list')

    def test_my_reports(self):
        self.create_report()
        token = self.login(self.student.username)
        self.auth(token)
        response = self.client.get(reverse('reports_api:my_reports'))
        self.assert_api_success(response, 'my reports')

    def test_submit_report(self):
        token = self.login(self.student.username)
        self.auth(token)
        response = self.client.post(
            reverse('reports_api:submit'),
            {
                'title': 'Submitted via API',
                'file': dummy_pdf(),
                'tags': 'api,test',
                'academic_year': '2025-2026',
            },
            format='multipart',
        )
        self.assert_api_success(response, 'submit report')
        self.assertEqual(response.data['data']['title'], 'Submitted via API')

    def test_submit_report_docx(self):
        token = self.login(self.student.username)
        self.auth(token)
        response = self.client.post(
            reverse('reports_api:submit'),
            {
                'title': 'DOCX submission',
                'file': dummy_docx(),
                'academic_year': '2025-2026',
            },
            format='multipart',
        )
        self.assert_api_success(response, 'submit docx report')

    def test_submit_group_report(self):
        mate = User.objects.create_user(
            username='student2',
            password=self.password,
            email='student2@test.com',
            role=User.Role.STUDENT,
            department=self.department_name,
            is_active=True,
            first_name='Mate',
            last_name='Two',
        )
        group = self.create_project_group(mate=mate, name='Group API Project')
        token = self.login(self.student.username)
        response = self.submit_group_report(
            token=token,
            group=group,
            title='Group API Project',
        )
        self.assert_api_success(response, 'submit group report')
        report = Report.objects.get(title='Group API Project')
        self.assertEqual(report.group_id, group.pk)
        self.assertEqual(report.assigned_teacher_id, self.teacher.pk)
        member_ids = set(report.group.members.values_list('pk', flat=True))
        self.assertEqual(member_ids, {self.student.pk, mate.pk})

    def test_group_mate_cannot_duplicate_submit(self):
        mate = User.objects.create_user(
            username='student2',
            password=self.password,
            email='student2@test.com',
            role=User.Role.STUDENT,
            department=self.department_name,
            is_active=True,
        )
        group = self.create_project_group(mate=mate, name='Duplicate Guard Group')
        submitter_token = self.login(self.student.username)
        first = self.submit_group_report(
            token=submitter_token,
            group=group,
            title='Shared Group Report',
        )
        self.assert_api_success(first, 'first group submit')

        mate_token = self.login(mate.username)
        duplicate = self.submit_group_report(
            token=mate_token,
            group=group,
            title='Mate Duplicate Attempt',
        )
        self.assertFalse(duplicate.data.get('success'))
        self.assertEqual(Report.objects.filter(group=group, is_deleted=False).count(), 1)

    def test_group_teacher_editable_from_report_detail(self):
        mate = User.objects.create_user(
            username='editmate',
            password=self.password,
            email='editmate@test.com',
            role=User.Role.STUDENT,
            department=self.department_name,
            is_active=True,
        )
        teacher_two = User.objects.create_user(
            username='teach_edit',
            password=self.password,
            email='teach_edit@test.com',
            role=User.Role.TEACHER,
            department=self.department_name,
            is_active=True,
            first_name='Edit',
            last_name='Teacher',
        )
        group = self.create_project_group(mate=mate, name='Editable Group')
        token = self.login(self.student.username)
        submit = self.submit_group_report(token=token, group=group, title='Editable Group Report')
        self.assert_api_success(submit, 'group submit')
        report = Report.objects.get(group=group, is_deleted=False)

        admin_token = self.login(self.admin.username)
        self.auth(admin_token)
        change = self.client.post(
            reverse('reports_api:assign_teacher', kwargs={'pk': report.pk}),
            {'teacher_id': teacher_two.pk},
            format='json',
        )
        self.assert_api_success(change, 'change group teacher via report')

        group.refresh_from_db()
        report.refresh_from_db()
        self.assertEqual(group.assigned_teacher_id, teacher_two.pk)
        self.assertEqual(report.assigned_teacher_id, teacher_two.pk)

        mate_notice = Notification.objects.filter(user=mate, message__icontains=teacher_two.department).exists()
        self.assertTrue(mate_notice, 'Group members notified when teacher edited from report')

    def test_group_mate_can_resubmit_rejected_report(self):
        mate = User.objects.create_user(
            username='student2',
            password=self.password,
            email='student2@test.com',
            role=User.Role.STUDENT,
            department=self.department_name,
            is_active=True,
        )
        group = self.create_project_group(mate=mate, name='Resubmit Group')
        submitter_token = self.login(self.student.username)
        self.assert_api_success(
            self.submit_group_report(token=submitter_token, group=group, title='Resubmit Group Report'),
            'initial group submit',
        )
        report = Report.objects.get(group=group, is_deleted=False)
        report.status = Report.Status.REJECTED
        report.save(update_fields=['status'])

        mate_token = self.login(mate.username)
        resubmit = self.client.post(
            reverse('reports_api:resubmit', kwargs={'pk': report.pk}),
            {'file': dummy_pdf('mate_resubmit.pdf')},
            format='multipart',
        )
        self.assert_api_success(resubmit, 'mate resubmit')
        report.refresh_from_db()
        self.assertEqual(report.attempt_count, 2)


    def test_student_multiple_projects_and_per_report_teachers(self):
        teacher_two = User.objects.create_user(
            username='teach2',
            password=self.password,
            email='teacher2@test.com',
            role=User.Role.TEACHER,
            department=self.department_name,
            is_active=True,
        )
        mate = User.objects.create_user(
            username='student2',
            password=self.password,
            email='student2@test.com',
            role=User.Role.STUDENT,
            department=self.department_name,
            is_active=True,
            first_name='Mate',
            last_name='Two',
        )
        student_token = self.login(self.student.username)

        individual = self.client.post(
            reverse('reports_api:submit'),
            {
                'title': 'Individual Project',
                'file': dummy_pdf('individual.pdf'),
                'academic_year': '2025-2026',
                'submission_type': 'individual',
            },
            format='multipart',
        )
        self.assert_api_success(individual, 'individual submit')

        group_alpha = self.create_project_group(mate=mate, name='Group Alpha', assign_teacher=self.teacher)
        group_beta = self.create_project_group(mate=mate, name='Group Beta', assign_teacher=teacher_two)

        group_one = self.submit_group_report(
            token=student_token,
            group=group_alpha,
            title='Group Project Alpha',
            filename='group1.pdf',
        )
        self.assert_api_success(group_one, 'group one submit')

        group_two = self.submit_group_report(
            token=student_token,
            group=group_beta,
            title='Group Project Beta',
            filename='group2.pdf',
        )
        self.assert_api_success(group_two, 'group two submit')

        reports = Report.objects.filter(
            Q(student=self.student) | Q(group__members=self.student)
        ).distinct()
        self.assertEqual(reports.count(), 3)

        admin_token = self.login(self.admin.username)
        self.auth(admin_token)
        individual_report = Report.objects.get(title='Individual Project')
        group_beta = Report.objects.get(title='Group Project Beta')

        assign_one = self.client.post(
            reverse('reports_api:assign_teacher', kwargs={'pk': individual_report.pk}),
            {'teacher_id': self.teacher.pk},
            format='json',
        )
        self.assert_api_success(assign_one, 'assign teacher one')
        assign_two = self.client.post(
            reverse('reports_api:assign_teacher', kwargs={'pk': group_beta.pk}),
            {'teacher_id': teacher_two.pk},
            format='json',
        )
        self.assert_api_success(assign_two, 'assign teacher two')

        self.auth(self.login(self.teacher.username))
        teacher_one_list = self.client.get(reverse('reports_api:report_list'))
        self.assert_api_success(teacher_one_list, 'teacher one list')
        teacher_one_titles = {item['title'] for item in teacher_one_list.data['data']['results']}
        self.assertIn('Individual Project', teacher_one_titles)
        self.assertNotIn('Group Project Beta', teacher_one_titles)

        self.auth(self.login(teacher_two.username))
        teacher_two_list = self.client.get(reverse('reports_api:report_list'))
        self.assert_api_success(teacher_two_list, 'teacher two list')
        teacher_two_titles = {item['title'] for item in teacher_two_list.data['data']['results']}
        self.assertIn('Group Project Beta', teacher_two_titles)
        self.assertNotIn('Individual Project', teacher_two_titles)


class ReportDetailActionAPITests(APITestBase):
    def setUp(self):
        self.clear_auth()
        self.report = self.create_report()
        self.admin_token = self.login(self.admin.username)
        self.teacher_token = self.login(self.teacher.username)
        self.student_token = self.login(self.student.username)

    def test_report_detail(self):
        self.auth(self.student_token)
        response = self.client.get(reverse('reports_api:detail', kwargs={'pk': self.report.pk}))
        self.assert_api_success(response, 'report detail')

    def test_comment_and_bookmark(self):
        self.auth(self.student_token)
        comment_response = self.client.post(
            reverse('reports_api:comment', kwargs={'pk': self.report.pk}),
            {'message': 'Looks good so far.'},
            format='json',
        )
        self.assert_api_success(comment_response, 'comment')

        bookmark_response = self.client.post(reverse('reports_api:bookmark', kwargs={'pk': self.report.pk}))
        self.assert_api_success(bookmark_response, 'bookmark')

    def test_teacher_approve_with_criterion_fields(self):
        self.auth(self.teacher_token)
        response = self.client.post(
            reverse('reports_api:teacher_approve', kwargs={'pk': self.report.pk}),
            {
                'teacher_marks': 85,
                'feedback': 'Solid work.',
                'is_final_submission': 'on',
                'criterion_1': 8,
            },
            format='json',
        )
        self.assert_api_success(response, 'teacher approve')
        self.report.refresh_from_db()
        self.assertTrue(self.report.teacher_approved)

    def test_admin_approve_reject_pin_restore_delete(self):
        self.report.teacher_approved = True
        self.report.is_final_submission = True
        self.report.refresh_status_from_flags()
        self.report.save()

        self.auth(self.admin_token)
        approve_response = self.client.post(
            reverse('reports_api:admin_approve', kwargs={'pk': self.report.pk}),
            {'marks': 88},
            format='json',
        )
        self.assert_api_success(approve_response, 'admin approve')
        self.report.refresh_from_db()
        self.assertTrue(self.report.certificate_generated)
        self.assertTrue(self.report.certificate_verification_code)

        pin_response = self.client.post(reverse('reports_api:toggle_pin', kwargs={'pk': self.report.pk}))
        self.assert_api_success(pin_response, 'pin')

        delete_response = self.client.post(reverse('reports_api:delete', kwargs={'pk': self.report.pk}))
        self.assert_api_success(delete_response, 'delete')

        restore_response = self.client.post(reverse('reports_api:restore', kwargs={'pk': self.report.pk}))
        self.assert_api_success(restore_response, 'restore')

    def test_admin_approve_issues_certificate_with_missing_template_image(self):
        from apps.reports.infrastructure.models import CertificateTemplate

        template = CertificateTemplate.get_active()
        template.reference_image = 'certificate_templates/missing.png'
        template.use_reference_background = True
        template.save(update_fields=['reference_image', 'use_reference_background'])

        self.report.teacher_approved = True
        self.report.is_final_submission = True
        self.report.refresh_status_from_flags()
        self.report.save()

        self.auth(self.admin_token)
        approve_response = self.client.post(
            reverse('reports_api:admin_approve', kwargs={'pk': self.report.pk}),
            {'marks': 91},
            format='json',
        )
        self.assert_api_success(approve_response, 'admin approve with missing template image')
        self.report.refresh_from_db()
        self.assertTrue(self.report.certificate_generated)

        self.auth(self.student_token)
        cert_response = self.client.get(
            reverse('reports_api:certificate', kwargs={'pk': self.report.pk})
        )
        self.assertEqual(cert_response.status_code, 200)
        self.assertEqual(cert_response['Content-Type'], 'application/pdf')

    def test_teacher_and_admin_reject(self):
        rejected = self.create_report(title='Reject Me')
        self.auth(self.teacher_token)
        teacher_reject = self.client.post(
            reverse('reports_api:teacher_reject', kwargs={'pk': rejected.pk}),
            {'reason': 'Needs more detail.'},
            format='json',
        )
        self.assert_api_success(teacher_reject, 'teacher reject')

        pending_admin = self.create_report(title='Admin Reject')
        pending_admin.teacher_approved = True
        pending_admin.refresh_status_from_flags()
        pending_admin.save()
        self.auth(self.admin_token)
        admin_reject = self.client.post(
            reverse('reports_api:admin_reject', kwargs={'pk': pending_admin.pk}),
            {'reason': 'Does not meet standards.'},
            format='json',
        )
        self.assert_api_success(admin_reject, 'admin reject')

    def test_resubmit_after_rejection(self):
        rejected = self.create_report(title='Resubmit Me', status=Report.Status.REJECTED)
        self.auth(self.student_token)
        response = self.client.post(
            reverse('reports_api:resubmit', kwargs={'pk': rejected.pk}),
            {'file': dummy_pdf('resubmit.pdf')},
            format='multipart',
        )
        self.assert_api_success(response, 'resubmit')

    def test_extension_and_reeval_requests(self):
        self.auth(self.student_token)
        extension_response = self.client.post(
            reverse('reports_api:extension_request', kwargs={'pk': self.report.pk}),
            {'reason': 'Need one more week.'},
            format='json',
        )
        self.assert_api_success(extension_response, 'extension request')

        approved = self.create_report(
            title='Reeval Report',
            status=Report.Status.APPROVED,
            teacher_approved=True,
            admin_approved=True,
            marks=75,
        )
        reeval_response = self.client.post(
            reverse('reports_api:reeval_request', kwargs={'pk': approved.pk}),
            {'reason': 'Please review marks again.'},
            format='json',
        )
        self.assert_api_success(reeval_response, 'reeval request')

    def test_versions_and_certificate(self):
        self.auth(self.student_token)
        versions_response = self.client.get(
            reverse('reports_api:versions', kwargs={'pk': self.report.pk})
        )
        self.assert_api_success(versions_response, 'versions')

        cert_report = self.create_report(
            title='Certificate Report',
            status=Report.Status.APPROVED,
            teacher_approved=True,
            admin_approved=True,
            is_final_submission=True,
            marks=90,
        )
        cert_report.certificate_verification_code = 'test-verify-code-123'
        cert_report.save(update_fields=['certificate_verification_code'])
        cert_response = self.client.get(
            reverse('reports_api:certificate', kwargs={'pk': cert_report.pk})
        )
        self.assertEqual(cert_response.status_code, 200)
        self.assertEqual(cert_response['Content-Type'], 'application/pdf')

    def test_group_certificate_personalized_per_member(self):
        mate = User.objects.create_user(
            username='certmate',
            password=self.password,
            email='certmate@test.com',
            role=User.Role.STUDENT,
            department=self.department_name,
            is_active=True,
            first_name='Cert',
            last_name='Mate',
        )
        from apps.reports.group_helpers import create_project_group
        from application.services.certificate_service import CertificateService

        group = create_project_group(self.student, 'Group Cert Project', [mate.pk])
        report = self.create_report(
            title='Group Cert Project',
            status=Report.Status.APPROVED,
            teacher_approved=True,
            admin_approved=True,
            is_final_submission=True,
            marks=88,
        )
        report.group = group
        report.save(update_fields=['group'])

        service = CertificateService()
        submitter_code = service.ensure_verification_code_for_recipient(report, self.student)
        mate_code = service.ensure_verification_code_for_recipient(report, mate)
        self.assertNotEqual(submitter_code, mate_code)

        submitter_verify = service.verify_code(submitter_code)
        mate_verify = service.verify_code(mate_code)
        self.assertEqual(submitter_verify['student_name'], self.student.get_full_name())
        self.assertEqual(mate_verify['student_name'], mate.get_full_name())

        self.auth(self.login(mate.username))
        mate_cert = self.client.get(reverse('reports_api:certificate', kwargs={'pk': report.pk}))
        self.assertEqual(mate_cert.status_code, 200)
        self.assertEqual(mate_cert['Content-Type'], 'application/pdf')

    def test_admin_approve_issues_personalized_certificates_for_all_group_members(self):
        mate = User.objects.create_user(
            username='groupcertmate',
            password=self.password,
            email='groupcertmate@test.com',
            role=User.Role.STUDENT,
            department=self.department_name,
            is_active=True,
            first_name='Group',
            last_name='CertMate',
        )
        group = self.create_project_group(mate=mate, name='All Cert Group')
        submit_response = self.submit_group_report(
            token=self.login(self.student.username),
            group=group,
            title='All Members Cert Project',
        )
        self.assertEqual(submit_response.status_code, 201)
        report = Report.objects.get(title='All Members Cert Project')
        report.teacher_approved = True
        report.is_final_submission = True
        report.refresh_status_from_flags()
        report.save()

        self.auth(self.admin_token)
        approve_response = self.client.post(
            reverse('reports_api:admin_approve', kwargs={'pk': report.pk}),
            {'marks': 87},
            format='json',
        )
        self.assert_api_success(approve_response, 'group admin approve')
        report.refresh_from_db()
        self.assertTrue(report.certificate_generated)
        self.assertTrue(report.certificate_verification_code)
        member_codes = report.certificate_member_codes_json or {}
        self.assertIn(str(mate.pk), member_codes)

        from application.services.certificate_service import CertificateService

        service = CertificateService()
        mate_verify = service.verify_code(member_codes[str(mate.pk)])
        self.assertEqual(mate_verify['student_name'], mate.get_full_name())
        self.assertTrue(mate_verify['is_group_project'])


class CertificateCelebrationTests(APITestBase):
    def test_student_dashboard_shows_celebration_until_acknowledged(self):
        report = self.create_report(
            title='Celebration Project',
            status=Report.Status.APPROVED,
            teacher_approved=True,
            admin_approved=True,
            is_final_submission=True,
            marks=92,
        )
        report.certificate_generated = True
        report.save(update_fields=['certificate_generated'])

        self.client.force_login(self.student)
        response = self.client.get(reverse('dashboard:student_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'certCelebrationRoot')
        self.assertContains(response, 'Congratulations!')
        self.assertContains(response, 'Celebration Project')

        ack = self.client.post(reverse('reports:certificate_celebration_ack', kwargs={'pk': report.pk}))
        self.assertEqual(ack.status_code, 200)
        self.assertTrue(ack.json()['success'])

        response_after = self.client.get(reverse('dashboard:student_dashboard'))
        self.assertNotContains(response_after, 'certCelebrationRoot')

    def test_group_member_gets_own_celebration(self):
        mate = User.objects.create_user(
            username='celebmate',
            password=self.password,
            email='celebmate@test.com',
            role=User.Role.STUDENT,
            department=self.department_name,
            is_active=True,
        )
        group = self.create_project_group(mate=mate, name='Celebration Group')
        report = self.create_report(
            title='Group Celebration Project',
            status=Report.Status.APPROVED,
            teacher_approved=True,
            admin_approved=True,
            is_final_submission=True,
            marks=90,
        )
        report.group = group
        report.certificate_generated = True
        report.save(update_fields=['group', 'certificate_generated'])

        self.client.force_login(mate)
        response = self.client.get(reverse('dashboard:student_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'certCelebrationRoot')
        self.assertContains(response, 'Group Celebration Project')


class ReportAdminUtilityAPITests(APITestBase):
    def setUp(self):
        self.admin_token = self.login(self.admin.username)

    def test_bulk_action(self):
        report_a = self.create_report(title='Bulk A')
        report_b = self.create_report(title='Bulk B')
        report_a.teacher_approved = True
        report_a.save(update_fields=['teacher_approved'])
        report_b.teacher_approved = True
        report_b.save(update_fields=['teacher_approved'])

        self.auth(self.admin_token)
        response = self.client.post(
            reverse('reports_api:bulk_action'),
            {'report_ids': [report_a.pk, report_b.pk], 'action': 'approve'},
            format='json',
        )
        self.assert_api_success(response, 'bulk action')

    def test_system_settings(self):
        self.auth(self.admin_token)
        get_response = self.client.get(reverse('reports_api:settings'))
        self.assert_api_success(get_response, 'settings get')

        put_response = self.client.put(
            reverse('reports_api:settings'),
            {
                'max_attempts': 6,
                'max_file_size_mb': 12,
                'group_max_attempts': 4,
                'group_min_members': 2,
                'group_max_members': 5,
            },
            format='json',
        )
        self.assert_api_success(put_response, 'settings put')

    def test_leaderboard_analytics_activity_tracking_extensions(self):
        self.create_report()
        self.auth(self.admin_token)

        leaderboard = self.client.get(reverse('reports_api:leaderboard'))
        self.assert_api_success(leaderboard, 'leaderboard')

        analytics = self.client.get(reverse('reports_api:analytics'))
        self.assert_api_success(analytics, 'analytics')

        activity = self.client.get(reverse('reports_api:activity_log'))
        self.assert_api_success(activity, 'activity log')

        tracking = self.client.get(reverse('reports_api:submission_tracking'))
        self.assert_api_success(tracking, 'submission tracking')

        extension = self.create_extension_request()
        queue = self.client.get(reverse('reports_api:extension_queue'))
        self.assert_api_success(queue, 'extension queue')

        resolve = self.client.post(
            reverse('reports_api:extension_resolve', kwargs={'pk': extension.pk}),
            {'decision': 'approve', 'note': 'Approved in test.'},
            format='json',
        )
        self.assert_api_success(resolve, 'extension resolve')

    def test_reeval_resolve(self):
        reeval = self.create_reeval_request()
        self.auth(self.admin_token)
        response = self.client.post(
            reverse('reports_api:reeval_resolve', kwargs={'reeval_pk': reeval.pk}),
            {'resolve_action': 'approve', 'updated_marks': 92},
            format='json',
        )
        self.assert_api_success(response, 'reeval resolve')

    def test_teacher_assigned_and_workload(self):
        self.create_report()
        self.auth(self.login(self.teacher.username))
        assigned = self.client.get(reverse('reports_api:teacher_assigned'))
        self.assert_api_success(assigned, 'teacher assigned')

        workload = self.client.get(reverse('reports_api:teacher_workload'))
        self.assert_api_success(workload, 'teacher workload')


class ReportNotificationAPITests(APITestBase):
    def test_notification_endpoints(self):
        note = self.create_notification()
        token = self.login(self.student.username)
        self.auth(token)

        list_response = self.client.get(reverse('reports_api:notifications'))
        self.assert_api_success(list_response, 'notifications list')

        read_response = self.client.post(
            reverse('reports_api:notification_read', kwargs={'pk': note.pk})
        )
        self.assert_api_success(read_response, 'notification read')

        mark_all = self.client.post(reverse('reports_api:notifications_mark_all_read'))
        self.assert_api_success(mark_all, 'mark all read')

        delete_response = self.client.delete(
            reverse('reports_api:notification_delete', kwargs={'pk': note.pk})
        )
        self.assert_api_success(delete_response, 'notification delete')


class ReportAIAPITests(APITestBase):
    def test_ai_suggestions_and_process(self):
        report = self.create_report(title='AI Report')
        token = self.login(self.teacher.username)
        self.auth(token)

        suggestions = self.client.get(
            reverse('reports_api:ai_suggestions', kwargs={'pk': report.pk})
        )
        self.assert_api_success(suggestions, 'ai suggestions')

        process = self.client.post(
            reverse('reports_api:ai_process', kwargs={'pk': report.pk}),
            {},
            format='json',
        )
        self.assert_api_success(process, 'ai process')


class GroupMemberProfileViewTests(APITestBase):
    def test_teacher_can_view_group_mate_profile_and_sees_group_report(self):
        mate = User.objects.create_user(
            username='profilemate',
            password=self.password,
            email='profilemate@test.com',
            role=User.Role.STUDENT,
            department=self.department_name,
            is_active=True,
            first_name='Profile',
            last_name='Mate',
        )
        group = self.create_project_group(mate=mate, name='Profile Group')
        submit_response = self.submit_group_report(
            token=self.login(self.student.username),
            group=group,
            title='Group Profile Project',
        )
        self.assertEqual(submit_response.status_code, 201)
        report = Report.objects.get(title='Group Profile Project')

        self.client.force_login(self.teacher)
        mate_profile = self.client.get(
            reverse('reports:public_student', kwargs={'username': mate.username})
        )
        self.assertEqual(mate_profile.status_code, 200)
        self.assertContains(mate_profile, 'Group Profile Project')

        detail = self.client.get(reverse('reports:detail', kwargs={'pk': report.pk}))
        self.assertEqual(detail.status_code, 200)
        self.assertNotContains(detail, 'Project members')
        self.assertContains(detail, reverse('reports:group_member_profiles', kwargs={'pk': report.pk}))

        members_page = self.client.get(
            reverse('reports:group_member_profiles', kwargs={'pk': report.pk})
        )
        self.assertEqual(members_page.status_code, 200)
        self.assertContains(members_page, 'Profile Mate')
        self.assertContains(members_page, reverse('reports:public_student', kwargs={'username': mate.username}))

    def test_teacher_without_assignment_cannot_view_unrelated_group_mate(self):
        mate = User.objects.create_user(
            username='othermate',
            password=self.password,
            email='othermate@test.com',
            role=User.Role.STUDENT,
            department=self.department_name,
            is_active=True,
        )
        other_teacher = User.objects.create_user(
            username='otherteacher',
            password=self.password,
            email='otherteacher@test.com',
            role=User.Role.TEACHER,
            department=self.department_name,
            is_active=True,
        )
        group = self.create_project_group(mate=mate, name='Other Group', assign_teacher=other_teacher)
        self.submit_group_report(
            token=self.login(self.student.username),
            group=group,
            title='Other Teacher Group Project',
        )

        self.client.force_login(self.teacher)
        mate_profile = self.client.get(
            reverse('reports:public_student', kwargs={'username': mate.username})
        )
        self.assertEqual(mate_profile.status_code, 200)
        self.assertNotContains(mate_profile, 'Other Teacher Group Project')
        self.assertContains(mate_profile, 'No approved projects published on this portfolio yet.')
