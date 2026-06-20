"""Integration tests for /api/v1/auth/* and user management endpoints."""
from django.urls import reverse

from apps.accounts.infrastructure.models import User
from api.tests.base import APITestBase, dummy_pdf


class AuthLoginLogoutAPITests(APITestBase):
    def test_login_success(self):
        response = self.client.post(
            reverse('accounts_api:login'),
            {'username': self.student.username, 'password': self.password},
            format='json',
        )
        self.assert_api_success(response, 'login')
        self.assertIn('access', response.data['data']['tokens'])
        self.assertEqual(response.data['data']['user']['username'], self.student.username)

    def test_login_invalid_credentials(self):
        response = self.client.post(
            reverse('accounts_api:login'),
            {'username': self.student.username, 'password': 'wrong'},
            format='json',
        )
        self.assertFalse(response.data['success'])

    def test_login_ignores_stale_authorization_header(self):
        """Expired or invalid Bearer tokens must not block the public login endpoint."""
        self.auth('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.invalid')
        response = self.client.post(
            reverse('accounts_api:login'),
            {'username': self.admin.username, 'password': self.password},
            format='json',
        )
        self.assert_api_success(response, 'login with stale auth header')

    def test_logout(self):
        token = self.login(self.admin.username)
        self.auth(token)
        response = self.client.post(reverse('accounts_api:logout'), {'refresh': ''}, format='json')
        self.assert_api_success(response, 'logout')


class AuthProfileAPITests(APITestBase):
    def test_profile_get_and_patch(self):
        token = self.login(self.student.username)
        self.auth(token)

        get_response = self.client.get(reverse('accounts_api:profile'))
        self.assert_api_success(get_response, 'profile get')
        self.assertEqual(get_response.data['data']['username'], self.student.username)

        patch_response = self.client.patch(
            reverse('accounts_api:profile'),
            {'first_name': 'Updated', 'last_name': 'Student'},
            format='json',
        )
        self.assert_api_success(patch_response, 'profile patch')
        self.assertEqual(patch_response.data['data']['first_name'], 'Updated')

    def test_profile_photo_upload(self):
        token = self.login(self.student.username)
        self.auth(token)
        from django.core.files.uploadedfile import SimpleUploadedFile

        photo = SimpleUploadedFile(
            'avatar.jpg',
            b'\xff\xd8\xff\xe0' + b'\x00' * 100,
            content_type='image/jpeg',
        )
        response = self.client.post(
            reverse('accounts_api:profile_photo'),
            {'profile_photo': photo},
            format='multipart',
        )
        self.assert_api_success(response, 'profile photo')

    def test_change_password(self):
        profile_user = User.objects.create_user(
            username='profilepw1',
            password=self.password,
            email='profilepw1@test.com',
            role=User.Role.STUDENT,
            is_active=True,
        )
        token = self.login(profile_user.username)
        self.auth(token)
        response = self.client.post(
            reverse('accounts_api:change_password'),
            {'old_password': self.password, 'new_password': 'NewPass2'},
            format='json',
        )
        self.assert_api_success(response, 'change password')


class AuthRegistrationAPITests(APITestBase):
    def test_register_student(self):
        response = self.client.post(
            reverse('accounts_api:register_student'),
            {
                'username': 'newstudent',
                'email': 'newstudent@test.com',
                'password': 'RegPass12',
                'first_name': 'New',
                'last_name': 'Student',
                'department': self.department_name,
            },
            format='json',
        )
        self.assert_api_success(response, 'register student')

    def test_register_teacher(self):
        response = self.client.post(
            reverse('accounts_api:register_teacher'),
            {
                'username': 'newteacher',
                'email': 'newteacher@test.com',
                'password': 'RegPass12',
                'first_name': 'New',
                'last_name': 'Teacher',
                'department': self.department_name,
            },
            format='json',
        )
        self.assert_api_success(response, 'register teacher')

    def test_forgot_password(self):
        response = self.client.post(
            reverse('accounts_api:forgot_password'),
            {'email': self.student.email},
            format='json',
        )
        self.assert_api_success(response, 'forgot password')


class UserManagementAPITests(APITestBase):
    def setUp(self):
        self.clear_auth()
        self.admin_token = self.login(self.admin.username)

    def test_departments_list_and_create(self):
        self.auth(self.admin_token)
        list_response = self.client.get(reverse('accounts_api:departments'))
        self.assert_api_success(list_response, 'departments list')

        create_response = self.client.post(
            reverse('accounts_api:departments'),
            {'name': 'Electrical Engineering'},
            format='json',
        )
        self.assert_api_success(create_response, 'departments create')

    def test_teachers_by_department(self):
        self.auth(self.admin_token)
        response = self.client.get(
            reverse('accounts_api:teachers_by_department'),
            {'department': self.department_name},
        )
        self.assert_api_success(response, 'teachers by department')
        self.assertGreaterEqual(len(response.data['data']), 1)

    def test_inline_teacher_create_emails_credentials(self):
        self.auth(self.admin_token)
        from django.core import mail

        mail.outbox.clear()
        response = self.client.post(
            reverse('accounts_api:user_create'),
            {
                'email': 'inlineteacher@test.com',
                'first_name': 'Inline',
                'last_name': 'Teacher',
                'role': 'teacher',
                'department': self.department_name,
            },
            format='json',
        )
        self.assert_api_success(response, 'inline teacher create')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['inlineteacher@test.com'])
        self.assertIn('Username:', mail.outbox[0].body)
        self.assertIn('Password:', mail.outbox[0].body)
        self.assertIn('Teacher', mail.outbox[0].body)

    def test_student_with_new_teacher_both_receive_credentials(self):
        """Simulates admin adding a teacher inline, then creating the student."""
        self.auth(self.admin_token)
        from django.core import mail

        mail.outbox.clear()
        teacher_response = self.client.post(
            reverse('accounts_api:user_create'),
            {
                'email': 'studentteacher@test.com',
                'first_name': 'Assigned',
                'last_name': 'Teacher',
                'role': 'teacher',
                'department': self.department_name,
            },
            format='json',
        )
        self.assert_api_success(teacher_response, 'create teacher for student')
        teacher_id = teacher_response.data['data']['user']['id']

        student_response = self.client.post(
            reverse('accounts_api:user_create'),
            {
                'email': 'newstudentflow@test.com',
                'first_name': 'Flow',
                'last_name': 'Student',
                'role': 'student',
                'department': self.department_name,
                'assigned_teacher_id': teacher_id,
            },
            format='json',
        )
        self.assert_api_success(student_response, 'create student with new teacher')
        self.assertEqual(len(mail.outbox), 2)
        recipients = {msg.to[0] for msg in mail.outbox}
        self.assertEqual(recipients, {'studentteacher@test.com', 'newstudentflow@test.com'})
        for msg in mail.outbox:
            self.assertIn('Username:', msg.body)
            self.assertIn('Password:', msg.body)

    def test_user_create_approve_update_assign_delete(self):
        self.auth(self.admin_token)
        create_response = self.client.post(
            reverse('accounts_api:user_create'),
            {
                'email': 'created@test.com',
                'first_name': 'Created',
                'last_name': 'User',
                'role': 'student',
                'department': self.department_name,
                'assigned_teacher_id': self.teacher.pk,
            },
            format='json',
        )
        self.assert_api_success(create_response, 'user create')
        user_id = create_response.data['data']['user']['id']

        approve_response = self.client.post(reverse('accounts_api:user_approve', kwargs={'pk': user_id}))
        self.assert_api_success(approve_response, 'user approve')

        patch_response = self.client.patch(
            reverse('accounts_api:user_update', kwargs={'pk': user_id}),
            {'first_name': 'Edited'},
            format='json',
        )
        self.assert_api_success(patch_response, 'user update')

        assign_response = self.client.post(
            reverse('accounts_api:assign_teacher', kwargs={'pk': user_id}),
            {'teacher_id': self.teacher.pk},
            format='json',
        )
        self.assert_api_success(assign_response, 'assign teacher')

        students_response = self.client.get(
            reverse('accounts_api:teacher_students', kwargs={'pk': self.teacher.pk})
        )
        self.assert_api_success(students_response, 'teacher students')

        deactivate_response = self.client.post(
            reverse('accounts_api:user_set_active', kwargs={'pk': user_id}),
            {'is_active': False},
            format='json',
        )
        self.assert_api_success(deactivate_response, 'user set active')

        delete_response = self.client.delete(reverse('accounts_api:user_delete', kwargs={'pk': user_id}))
        self.assert_api_success(delete_response, 'user delete')

    def test_user_list_and_pending_students(self):
        self.auth(self.admin_token)
        list_response = self.client.get(reverse('accounts_api:user_list'))
        self.assert_api_success(list_response, 'user list')

        self.auth(self.login(self.teacher.username))
        pending_response = self.client.get(reverse('accounts_api:pending_students'))
        self.assert_api_success(pending_response, 'pending students')
