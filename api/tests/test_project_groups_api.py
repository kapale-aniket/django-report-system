"""Integration tests for /api/v1/project-groups/* endpoints."""
from django.contrib.auth import get_user_model
from django.urls import reverse

from api.tests.base import APITestBase, dummy_pdf
from apps.reports.infrastructure.models import Notification

User = get_user_model()


class ProjectGroupAPITests(APITestBase):
    def test_create_list_and_assign_teacher(self):
        mate = User.objects.create_user(
            username='pgmate',
            password=self.password,
            email='pgmate@test.com',
            role=User.Role.STUDENT,
            department=self.department_name,
            is_active=True,
        )
        student_token = self.login(self.student.username)
        self.auth(student_token)
        create_response = self.client.post(
            reverse('project_groups_api:create'),
            {
                'name': 'API Created Group',
                'description': 'Public group',
                'project_mate_ids': str(mate.pk),
            },
            format='json',
        )
        self.assert_api_success(create_response, 'create project group')
        group_id = create_response.data['data']['id']

        list_response = self.client.get(reverse('project_groups_api:list'))
        self.assert_api_success(list_response, 'list public groups')

        my_response = self.client.get(reverse('project_groups_api:my'))
        self.assert_api_success(my_response, 'list my groups')

        admin_token = self.login(self.admin.username)
        self.auth(admin_token)
        assign_response = self.client.post(
            reverse('project_groups_api:assign_teacher', kwargs={'pk': group_id}),
            {'teacher_id': self.teacher.pk},
            format='json',
        )
        self.assert_api_success(assign_response, 'assign group teacher')

        member_notifications = Notification.objects.filter(
            user=mate,
            message__icontains=self.teacher.department,
        )
        self.assertTrue(member_notifications.exists(), 'Group mate should be notified with teacher department')

        self.auth(student_token)
        submittable = self.client.get(reverse('project_groups_api:submittable'))
        self.assert_api_success(submittable, 'submittable groups')
        submittable_ids = {item['id'] for item in submittable.data['data']}
        self.assertIn(group_id, submittable_ids)

        submit = self.client.post(
            reverse('reports_api:submit'),
            {
                'title': 'Group Submit After Assign',
                'file': dummy_pdf('assigned_group.pdf'),
                'academic_year': '2025-2026',
                'submission_type': 'group',
                'project_group_id': group_id,
            },
            format='multipart',
        )
        self.assert_api_success(submit, 'submit after teacher assigned')

        teacher_notification = Notification.objects.filter(
            user=self.teacher,
            message__icontains='submitted',
        )
        self.assertTrue(teacher_notification.exists(), 'Assigned teacher should be notified on group submit')

    def test_group_member_count_rules_enforced(self):
        from apps.reports.infrastructure.models import SystemSettings

        settings = SystemSettings.get_settings()
        settings.group_min_members = 3
        settings.group_max_members = 4
        settings.save(update_fields=['group_min_members', 'group_max_members'])

        mate_one = User.objects.create_user(
            username='gmate1',
            password=self.password,
            email='gmate1@test.com',
            role=User.Role.STUDENT,
            department=self.department_name,
            is_active=True,
        )
        mate_two = User.objects.create_user(
            username='gmate2',
            password=self.password,
            email='gmate2@test.com',
            role=User.Role.STUDENT,
            department=self.department_name,
            is_active=True,
        )
        student_token = self.login(self.student.username)
        self.auth(student_token)

        too_few = self.client.post(
            reverse('project_groups_api:create'),
            {'name': 'Too Small', 'project_mate_ids': str(mate_one.pk)},
            format='json',
        )
        self.assertFalse(too_few.data.get('success'))

        ok = self.client.post(
            reverse('project_groups_api:create'),
            {'name': 'Valid Size', 'project_mate_ids': f'{mate_one.pk},{mate_two.pk}'},
            format='json',
        )
        self.assert_api_success(ok, 'valid group size')
