from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated

from api.base.base_api_view import BaseAPIView
from api.serializers.auth import (
    AssignTeacherSerializer,
    ChangePasswordSerializer,
    CreateUserSerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    UserListFilterSerializer,
    UserProfileSerializer,
    AdminUserUpdateSerializer,
    CreateDepartmentSerializer,
    TeacherListFilterSerializer,
    TeacherOptionSerializer,
    UserActiveSerializer,
)
from application.services.auth_service import AuthService
from application.services.user_management_service import UserManagementService
from core.constants.roles import UserRole
from core.exceptions import PermissionAppError
from core.permissions.roles import IsAdmin, IsTeacher

User = get_user_model()


class LoginAPIView(BaseAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        auth_service = AuthService()
        result = self.run_service(
            lambda: auth_service.login(serializer.to_dto()),
            action='login',
        )
        user = User.objects.filter(pk=result['user']['id']).first()
        if user:
            from django.contrib.auth import login as django_login

            django_login(request, user)
        self.log_action('login', user=user, detail='JWT + session issued')
        return self.success(data=result, message='Login successful')


class LogoutAPIView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        auth_service = AuthService()
        self.run_service(
            lambda: auth_service.logout(serializer.validated_data.get('refresh', '')),
            action='logout',
            user=request.user,
        )
        return self.success(message='Logged out successfully')


class RegisterStudentAPIView(BaseAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        auth_service = AuthService()
        profile = self.run_service(
            lambda: auth_service.register_student(serializer.to_dto()),
            action='register_student',
        )
        return self.success(
            data=UserProfileSerializer(profile.to_dict()).data,
            message='Registration received. Your account is pending approval.',
            status_code=status.HTTP_201_CREATED,
        )


class RegisterTeacherAPIView(BaseAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        auth_service = AuthService()
        profile = self.run_service(
            lambda: auth_service.register_teacher(serializer.to_dto()),
            action='register_teacher',
        )
        return self.success(
            data=UserProfileSerializer(profile.to_dict()).data,
            message='Registration received. Your account is pending administrator approval.',
            status_code=status.HTTP_201_CREATED,
        )


class ProfileAPIView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        auth_service = AuthService()
        profile = self.run_service(
            lambda: auth_service.get_profile(request.user.pk),
            action='get_profile',
            user=request.user,
        )
        return self.success(data=UserProfileSerializer(profile).data, message='Profile retrieved')

    def patch(self, request):
        serializer = ProfileUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        auth_service = AuthService()
        profile = self.run_service(
            lambda: auth_service.update_profile(request.user.pk, serializer.to_dto()),
            action='update_profile',
            user=request.user,
        )
        return self.success(data=UserProfileSerializer(profile).data, message='Profile updated')


class ProfilePhotoAPIView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        photo = request.FILES.get('profile_photo')
        auth_service = AuthService()
        profile = self.run_service(
            lambda: auth_service.update_profile_photo(request.user.pk, photo),
            action='update_profile_photo',
            user=request.user,
        )
        return self.success(data=UserProfileSerializer(profile).data, message='Profile photo updated')


class ChangePasswordAPIView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        auth_service = AuthService()
        self.run_service(
            lambda: auth_service.change_password(request.user.pk, serializer.to_dto()),
            action='change_password',
            user=request.user,
        )
        return self.success(message='Password changed successfully')


class ForgotPasswordAPIView(BaseAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        auth_service = AuthService()
        self.run_service(
            lambda: auth_service.forgot_password(serializer.validated_data['email']),
            action='forgot_password',
        )
        return self.success(
            message='If an account exists for that email, password reset instructions have been sent.'
        )


class ResetPasswordAPIView(BaseAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        auth_service = AuthService()
        profile = self.run_service(
            lambda: auth_service.reset_password(
                serializer.validated_data['uid'],
                serializer.validated_data['token'],
                serializer.validated_data['new_password'],
            ),
            action='reset_password',
        )
        return self.success(
            data=UserProfileSerializer(profile.to_dict()).data,
            message='Password reset successful',
        )


class UserListAPIView(BaseAPIView):
    permission_classes = [IsAdmin]
    search_fields = ['username', 'first_name', 'last_name', 'email']
    ordering_fields = ['username', 'role', 'id']
    ordering = ['role', 'username']

    def get(self, request):
        filters = UserListFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        role = filters.validated_data.get('role') or None
        search = filters.validated_data.get('search', '')
        user_service = UserManagementService()
        users = self.run_service(
            lambda: user_service.list_users(role=role, search=search),
            action='list_users',
            user=request.user,
        )
        page = self.paginate_queryset(users)
        if page is not None:
            serialized = UserProfileSerializer(page, many=True).data
            return self.get_paginated_response(serialized)
        return self.success(
            data=UserProfileSerializer(users, many=True).data,
            message='Users retrieved successfully',
        )


class UserApproveAPIView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        actor_role = getattr(request.user, 'role', '')
        if actor_role not in (UserRole.ADMIN.value, UserRole.TEACHER.value):
            raise PermissionAppError('Permission denied')

        user_service = UserManagementService()
        profile = self.run_service(
            lambda: user_service.approve_user(request.user.pk, actor_role, pk),
            action='approve_user',
            user=request.user,
        )
        return self.success(
            data=UserProfileSerializer(profile.to_dict()).data,
            message=f'User {profile.username} approved',
        )


class UserDeleteAPIView(BaseAPIView):
    permission_classes = [IsAdmin]

    def delete(self, request, pk):
        user_service = UserManagementService()
        self.run_service(
            lambda: user_service.delete_user(request.user.pk, pk),
            action='delete_user',
            user=request.user,
        )
        return self.success(message='User deleted successfully')


class UserUpdateAPIView(BaseAPIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        serializer = AdminUserUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user_service = UserManagementService()
        profile = self.run_service(
            lambda: user_service.update_user(request.user.pk, pk, serializer.validated_data),
            action='update_user',
            user=request.user,
        )
        return self.success(
            data=UserProfileSerializer(profile.to_dict()).data,
            message='User updated successfully',
        )


class UserSetActiveAPIView(BaseAPIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        serializer = UserActiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_service = UserManagementService()
        profile = self.run_service(
            lambda: user_service.set_user_active(
                request.user.pk,
                pk,
                is_active=serializer.validated_data['is_active'],
            ),
            action='set_user_active',
            user=request.user,
        )
        state = 'activated' if profile.is_active else 'deactivated'
        return self.success(
            data=UserProfileSerializer(profile.to_dict()).data,
            message=f'User {profile.username} {state}',
        )


class AssignTeacherAPIView(BaseAPIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        serializer = AssignTeacherSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_service = UserManagementService()
        profile = self.run_service(
            lambda: user_service.assign_teacher(
                pk,
                serializer.validated_data.get('teacher_id'),
            ),
            action='assign_teacher',
            user=request.user,
        )
        return self.success(
            data=UserProfileSerializer(profile.to_dict()).data,
            message='Teacher assignment updated',
        )


class PendingStudentsAPIView(BaseAPIView):
    permission_classes = [IsTeacher]

    def get(self, request):
        user_service = UserManagementService()
        students = self.run_service(
            lambda: user_service.pending_students(request.user.pk),
            action='pending_students',
            user=request.user,
        )
        page = self.paginate_queryset(students)
        if page is not None:
            serialized = UserProfileSerializer(page, many=True).data
            return self.get_paginated_response(serialized)
        return self.success(
            data=UserProfileSerializer(students, many=True).data,
            message='Pending students retrieved',
        )


class TeacherStudentsAPIView(BaseAPIView):
    permission_classes = [IsAdmin]

    def get(self, request, pk):
        user_service = UserManagementService()
        students = self.run_service(
            lambda: user_service.list_teacher_students(pk),
            action='list_teacher_students',
            user=request.user,
        )
        return self.success(data=students, message='Assigned students retrieved')


class TeachersByDepartmentAPIView(BaseAPIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        filters = TeacherListFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        department = (filters.validated_data.get('department') or '').strip()
        user_service = UserManagementService()
        teachers = self.run_service(
            lambda: user_service.list_teachers_by_department(department),
            action='list_teachers_by_department',
            user=request.user,
        )
        return self.success(
            data=TeacherOptionSerializer(teachers, many=True).data,
            message='Teachers retrieved',
        )


class DepartmentListCreateAPIView(BaseAPIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        user_service = UserManagementService()
        departments = self.run_service(
            lambda: user_service.list_departments(),
            action='list_departments',
            user=request.user,
        )
        return self.success(data=departments, message='Departments retrieved')

    def post(self, request):
        serializer = CreateDepartmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_service = UserManagementService()
        department = self.run_service(
            lambda: user_service.create_department(serializer.validated_data['name']),
            action='create_department',
            user=request.user,
        )
        return self.success(
            data=department,
            message=f'Department "{department["name"]}" added',
            status_code=status.HTTP_201_CREATED,
        )


class CreateUserAPIView(BaseAPIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = CreateUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_service = UserManagementService()
        result = self.run_service(
            lambda: user_service.create_user(serializer.validated_data),
            action='create_user',
            user=request.user,
        )
        profile = result.profile
        payload = {'user': UserProfileSerializer(profile.to_dict()).data}
        if not result.email_sent:
            payload['login_details'] = {
                'username': profile.username,
                'password': result.password,
            }
        message = (
            f'User "{profile.username}" was created. Login details were emailed to {profile.email}.'
            if result.email_sent
            else (
                f'User "{profile.username}" was created, but the welcome email could not be sent. '
                f'{result.email_notice}'
            )
        )
        return self.success(
            data=payload,
            message=message,
            status_code=status.HTTP_201_CREATED,
        )
