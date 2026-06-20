from rest_framework import serializers

from application.dtos.auth import ChangePasswordDTO, LoginDTO, ProfileUpdateDTO, RegisterDTO
from apps.accounts.department_choices import ADD_DEPARTMENT_VALUE
from apps.accounts.infrastructure.models import User


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, write_only=True)
    role_hint = serializers.ChoiceField(
        choices=['admin', 'teacher', 'student', ''],
        required=False,
        allow_blank=True,
        default='',
    )

    def to_dto(self) -> LoginDTO:
        return LoginDTO(
            username=self.validated_data['username'],
            password=self.validated_data['password'],
            role_hint=self.validated_data.get('role_hint', ''),
        )


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, max_length=128, write_only=True)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    department = serializers.CharField(max_length=120, required=False, allow_blank=True, default='')

    def to_dto(self) -> RegisterDTO:
        return RegisterDTO(
            username=self.validated_data['username'],
            email=self.validated_data['email'],
            password=self.validated_data['password'],
            first_name=self.validated_data['first_name'],
            last_name=self.validated_data['last_name'],
            department=self.validated_data.get('department', ''),
        )


class ProfileUpdateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, required=False)
    email = serializers.EmailField(required=False)
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    department = serializers.CharField(max_length=120, required=False, allow_blank=True)

    def to_dto(self) -> ProfileUpdateDTO:
        return ProfileUpdateDTO(
            username=self.validated_data.get('username'),
            email=self.validated_data.get('email'),
            first_name=self.validated_data.get('first_name'),
            last_name=self.validated_data.get('last_name'),
            department=self.validated_data.get('department'),
        )


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(max_length=128, write_only=True)
    new_password = serializers.CharField(min_length=7, max_length=128, write_only=True)

    def to_dto(self) -> ChangePasswordDTO:
        return ChangePasswordDTO(
            old_password=self.validated_data['old_password'],
            new_password=self.validated_data['new_password'],
        )


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=7, max_length=128, write_only=True)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=False, allow_blank=True)


class UserProfileSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    role = serializers.CharField(read_only=True)
    department = serializers.CharField(read_only=True)
    roll_number = serializers.CharField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    first_name = serializers.CharField(read_only=True, required=False)
    last_name = serializers.CharField(read_only=True, required=False)
    assigned_teacher_id = serializers.IntegerField(read_only=True, required=False, allow_null=True)
    profile_photo = serializers.CharField(read_only=True, required=False, allow_blank=True)


class CreateUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default='')
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default='')
    role = serializers.ChoiceField(choices=[User.Role.TEACHER, User.Role.STUDENT])
    department = serializers.CharField(max_length=120, required=False, allow_blank=True, default='')
    assigned_teacher_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_email(self, value):
        from infrastructure.email.messages import normalize_email

        return normalize_email(value)

    def validate_department(self, value):
        department = (value or '').strip()
        if department == ADD_DEPARTMENT_VALUE:
            raise serializers.ValidationError('Select a department or use “Add department…” to create one first.')
        return department


class AssignTeacherSerializer(serializers.Serializer):
    teacher_id = serializers.IntegerField(required=False, allow_null=True)


class UserListFilterSerializer(serializers.Serializer):
    role = serializers.CharField(required=False, allow_blank=True, default='')
    search = serializers.CharField(required=False, allow_blank=True, default='')


class TeacherListFilterSerializer(serializers.Serializer):
    department = serializers.CharField(required=False, allow_blank=True, default='')


class TeacherOptionSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    first_name = serializers.CharField(read_only=True, required=False)
    last_name = serializers.CharField(read_only=True, required=False)
    full_name = serializers.CharField(read_only=True, required=False)
    department = serializers.CharField(read_only=True, required=False)


class AdminUserUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField(required=False)
    department = serializers.CharField(max_length=120, required=False, allow_blank=True)

    def validate_department(self, value):
        department = (value or '').strip()
        if department == ADD_DEPARTMENT_VALUE:
            raise serializers.ValidationError('Select a department or use “Add department…” to create one first.')
        return department


class UserActiveSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()


class DepartmentSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)


class CreateDepartmentSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)

    def validate_name(self, value):
        cleaned = (value or '').strip()
        if not cleaned:
            raise serializers.ValidationError('Department name is required.')
        return cleaned
