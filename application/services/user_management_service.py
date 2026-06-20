from apps.accounts.credential_utils import generate_short_password, generate_short_username
from apps.accounts.infrastructure.models import Department, User
from application.dtos.user_management import CreateUserResult
from core.constants.roles import UserRole
from core.exceptions import (
    AuthenticationAppError,
    BusinessLogicError,
    NotFoundAppError,
    PermissionAppError,
    ValidationAppError,
)
from core.services.base import BaseService
from domain.accounts.entities import UserProfile
from infrastructure.email.messages import friendly_email_send_error, friendly_validation_message, normalize_email
from infrastructure.email.smtp_sender import send_welcome_credentials_email
from infrastructure.repositories.user_repository import UserRepository


class UserManagementService(BaseService[UserRepository]):
    """Admin/teacher user management business logic."""

    repository_class = UserRepository

    def __init__(self, repository: UserRepository | None = None):
        super().__init__(repository=repository or UserRepository())

    def list_users(self, *, role: str | None = None, search: str = '') -> list[dict]:
        profiles = self.repository.list_users(
            role=role,
            search=search,
            exclude_roles=[UserRole.ADMIN.value],
        )
        return [self._enrich_profile(p) for p in profiles]

    def _enrich_profile(self, profile: UserProfile) -> dict:
        detail = self.repository.get_user_detail(profile.id)
        return detail or profile.to_dict()

    def _guard_target_mutation(self, actor_id: int, target_id: int) -> UserProfile:
        if actor_id == target_id:
            raise BusinessLogicError('Cannot modify your own account')
        target = self.repository.get_by_id(target_id)
        if target is None:
            raise NotFoundAppError('User not found')
        if target.role == UserRole.ADMIN.value:
            raise BusinessLogicError('Use superuser tools for admin accounts')
        return target

    def approve_user(self, actor_id: int, actor_role: str, target_id: int) -> UserProfile:
        target = self.repository.get_by_id(target_id)
        if target is None:
            raise NotFoundAppError('User not found')

        actor = self.repository.get_by_id(actor_id)
        if actor is None:
            raise AuthenticationAppError('Authentication required')

        if target_id == actor_id:
            raise BusinessLogicError('Cannot modify your own account')

        if target.role == UserRole.ADMIN.value:
            raise BusinessLogicError('Use superuser tools for admin accounts')

        if actor_role == UserRole.TEACHER.value:
            if target.role != UserRole.STUDENT.value:
                raise PermissionAppError('Teachers can only approve students')
            detail = self.repository.get_user_detail(target_id) or {}
            if detail.get('assigned_teacher_id') != actor_id:
                raise PermissionAppError('You can only approve students assigned to you')
        elif actor_role != UserRole.ADMIN.value:
            raise PermissionAppError('Permission denied')

        try:
            return self.repository.update(target_id, {'is_active': True})
        except User.DoesNotExist:
            raise NotFoundAppError('User not found') from None

    def set_user_active(self, actor_id: int, target_id: int, *, is_active: bool) -> UserProfile:
        self._guard_target_mutation(actor_id, target_id)
        try:
            return self.repository.update(target_id, {'is_active': is_active})
        except User.DoesNotExist:
            raise NotFoundAppError('User not found') from None

    def update_user(self, actor_id: int, target_id: int, data: dict) -> UserProfile:
        self._guard_target_mutation(actor_id, target_id)
        email = (data.get('email') or '').strip()
        if email and self.repository.email_exists(email, exclude_id=target_id):
            raise ValidationAppError('Email is already registered')
        payload = {}
        for key in ('first_name', 'last_name', 'email', 'department'):
            if key in data and data[key] is not None:
                payload[key] = data[key]
        if not payload:
            raise ValidationAppError('No fields to update')
        try:
            return self.repository.update(target_id, payload)
        except User.DoesNotExist:
            raise NotFoundAppError('User not found') from None

    def delete_user(self, actor_id: int, target_id: int) -> None:
        self._guard_target_mutation(actor_id, target_id)

        try:
            self.repository.delete(target_id)
        except User.DoesNotExist:
            raise NotFoundAppError('User not found') from None

    def assign_teacher(self, student_id: int, teacher_id: int | None) -> UserProfile:
        student = self.repository.get_by_id(student_id)
        if student is None:
            raise NotFoundAppError('Student not found')
        if student.role != UserRole.STUDENT.value:
            raise BusinessLogicError('Teacher assignment applies to students only')

        try:
            return self.repository.assign_teacher(student_id, teacher_id)
        except User.DoesNotExist:
            raise ValidationAppError('Invalid teacher selected') from None

    def create_user(self, data: dict) -> CreateUserResult:
        email = normalize_email(data.get('email') or '')
        role = data.get('role', '')
        first_name = (data.get('first_name') or '').strip()
        last_name = (data.get('last_name') or '').strip()

        if not email or not role:
            raise ValidationAppError(friendly_validation_message('email and role are required'))
        if role == UserRole.ADMIN.value:
            raise ValidationAppError(friendly_validation_message('Cannot create admin accounts via API'))
        if self.repository.email_exists(email):
            raise ValidationAppError(friendly_validation_message('Email is already registered'))

        username = (data.get('username') or '').strip()
        if username:
            if len(username) > 7:
                raise ValidationAppError(friendly_validation_message('Username must be at most 7 characters'))
            if self.repository.username_exists(username):
                raise ValidationAppError(friendly_validation_message('Username is already taken'))
        else:
            username = generate_short_username(
                first_name=first_name,
                last_name=last_name,
                email=email,
                exists=self.repository.username_exists,
            )

        assigned_teacher_id = data.get('assigned_teacher_id')
        if role != UserRole.STUDENT.value:
            assigned_teacher_id = None
        elif assigned_teacher_id:
            teacher = self.repository.get_by_id(int(assigned_teacher_id))
            if teacher is None or teacher.role != UserRole.TEACHER.value:
                raise ValidationAppError(friendly_validation_message('Invalid teacher selected'))
            student_department = (data.get('department') or '').strip()
            teacher_department = (teacher.department or '').strip()
            if student_department and teacher_department:
                if student_department.casefold() != teacher_department.casefold():
                    raise ValidationAppError(
                        friendly_validation_message('Selected teacher does not belong to this department')
                    )

        raw_password = generate_short_password()
        create_data = {
            'username': username,
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'role': role,
            'department': data.get('department', ''),
            'password': raw_password,
            'is_active': True,
        }
        if assigned_teacher_id:
            create_data['assigned_teacher_id'] = assigned_teacher_id

        profile = self.repository.create(create_data)
        try:
            send_welcome_credentials_email(
                to_email=email,
                first_name=first_name or last_name,
                username=username,
                password=raw_password,
                role=role,
            )
        except Exception as exc:
            return CreateUserResult(
                profile=profile,
                password=raw_password,
                email_sent=False,
                email_notice=friendly_email_send_error(exc),
            )

        return CreateUserResult(
            profile=profile,
            password=raw_password,
            email_sent=True,
            email_notice=None,
        )

    def pending_students(self, teacher_id: int) -> list[dict]:
        profiles = self.repository.pending_students_for_teacher(teacher_id)
        return [self._enrich_profile(p) for p in profiles]

    def list_teacher_students(self, teacher_id: int) -> list[dict]:
        try:
            return self.repository.students_for_teacher(teacher_id)
        except User.DoesNotExist as exc:
            raise NotFoundAppError('Teacher not found') from exc

    def list_departments(self) -> list[dict]:
        return list(Department.objects.filter(is_active=True).order_by('name').values('id', 'name'))

    def list_teachers_by_department(self, department: str) -> list[dict]:
        cleaned = (department or '').strip()
        if not cleaned:
            return []
        teachers = User.objects.filter(
            role=User.Role.TEACHER,
            is_active=True,
            department__iexact=cleaned,
        ).order_by('username')
        return [
            {
                'id': teacher.pk,
                'username': teacher.username,
                'first_name': teacher.first_name,
                'last_name': teacher.last_name,
                'full_name': teacher.get_full_name().strip() or teacher.username,
                'department': teacher.department or '',
            }
            for teacher in teachers
        ]

    def create_department(self, name: str) -> dict:
        cleaned_name = (name or '').strip()
        if not cleaned_name:
            raise ValidationAppError('Department name is required')
        if len(cleaned_name) > 120:
            raise ValidationAppError('Department name must be 120 characters or fewer')

        department, created = Department.objects.get_or_create(
            name=cleaned_name,
            defaults={'is_active': True},
        )
        if not created and not department.is_active:
            department.is_active = True
            department.save(update_fields=['is_active'])
        return {'id': department.pk, 'name': department.name}
