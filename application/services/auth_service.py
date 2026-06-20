from django.conf import settings
from django.core.mail import send_mail

from application.dtos.auth import ChangePasswordDTO, LoginDTO, ProfileUpdateDTO, RegisterDTO
from core.constants.roles import UserRole
from core.exceptions import AuthenticationAppError, NotFoundAppError, ValidationAppError
from core.services.base import BaseService
from domain.accounts.entities import UserProfile
from infrastructure.repositories.user_repository import UserRepository


class AuthService(BaseService[UserRepository]):
    """Authentication and profile business logic."""

    repository_class = UserRepository

    INACTIVE_MESSAGE = (
        'Your account is pending approval. Students: wait for an administrator or your assigned teacher. '
        'Teachers: wait for an administrator to activate your account.'
    )

    def __init__(self, repository: UserRepository | None = None):
        super().__init__(repository=repository or UserRepository())

    def login(self, dto: LoginDTO) -> dict:
        existing = self.repository.get_by_username(dto.username)
        if existing and not existing.is_active:
            raise AuthenticationAppError(self.INACTIVE_MESSAGE)

        profile = self.repository.authenticate(dto.username, dto.password)
        if profile is None:
            raise AuthenticationAppError('Invalid username or password')

        role_hint = (dto.role_hint or '').lower()
        if role_hint and role_hint in ('admin', 'teacher', 'student') and profile.role != role_hint:
            raise AuthenticationAppError(
                f'This account is registered as {profile.role}, not {role_hint}. '
                'Use the matching login endpoint for your role.'
            )

        tokens = self.repository.issue_jwt_tokens(profile.id)
        return {
            'tokens': tokens,
            'user': profile.to_dict(),
        }

    def logout(self, refresh_token: str) -> None:
        if refresh_token:
            self.repository.blacklist_refresh_token(refresh_token)

    def register_student(self, dto: RegisterDTO) -> UserProfile:
        return self._register(dto, role=UserRole.STUDENT.value)

    def register_teacher(self, dto: RegisterDTO) -> UserProfile:
        return self._register(dto, role=UserRole.TEACHER.value)

    def _register(self, dto: RegisterDTO, *, role: str) -> UserProfile:
        if self.repository.username_exists(dto.username):
            raise ValidationAppError('Username is already taken')
        if self.repository.email_exists(dto.email):
            raise ValidationAppError('Email is already registered')

        try:
            return self.repository.create(
                {
                    'username': dto.username,
                    'email': dto.email,
                    'password': dto.password,
                    'first_name': dto.first_name,
                    'last_name': dto.last_name,
                    'department': dto.department,
                    'role': role,
                    'is_active': False,
                }
            )
        except Exception as exc:
            raise ValidationAppError(str(exc)) from exc

    def get_profile(self, user_id: int) -> dict:
        detail = self.repository.get_profile_detail(user_id)
        if detail is None:
            raise NotFoundAppError('User not found')
        return detail

    def update_profile(self, user_id: int, dto: ProfileUpdateDTO) -> dict:
        data = {}
        current = self.repository.get_by_id(user_id)
        if current is None:
            raise NotFoundAppError('User not found')

        if dto.username is not None:
            username = dto.username.strip()
            if not username:
                raise ValidationAppError('Username cannot be empty')
            if len(username) > 150:
                raise ValidationAppError('Username must be at most 150 characters')
            if username != current.username and self.repository.username_exists(username):
                raise ValidationAppError('Username is already taken')
            data['username'] = username
        if dto.email is not None:
            if self.repository.email_exists(dto.email):
                if current.email.lower() != dto.email.lower():
                    raise ValidationAppError('Email is already registered')
            data['email'] = dto.email
        if dto.first_name is not None:
            data['first_name'] = dto.first_name
        if dto.last_name is not None:
            data['last_name'] = dto.last_name
        if dto.department is not None:
            data['department'] = dto.department

        if not data:
            raise ValidationAppError('No profile fields to update')

        try:
            self.repository.update(user_id, data)
        except Exception as exc:
            from apps.accounts.infrastructure.models import User

            if isinstance(exc, User.DoesNotExist):
                raise NotFoundAppError('User not found') from None
            raise

        detail = self.repository.get_profile_detail(user_id)
        return detail or {}

    def update_profile_photo(self, user_id: int, photo) -> dict:
        if photo is None:
            raise ValidationAppError('Profile photo is required')
        allowed = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
        content_type = getattr(photo, 'content_type', '') or ''
        if content_type not in allowed:
            raise ValidationAppError('Photo must be JPG, PNG, WEBP, or GIF')
        if photo.size > 2 * 1024 * 1024:
            raise ValidationAppError('Photo must be 2 MB or smaller')

        try:
            self.repository.update_profile_photo(user_id, photo)
        except Exception as exc:
            from apps.accounts.infrastructure.models import User

            if isinstance(exc, User.DoesNotExist):
                raise NotFoundAppError('User not found') from None
            raise ValidationAppError(str(exc)) from exc

        detail = self.repository.get_profile_detail(user_id)
        return detail or {}

    def change_password(self, user_id: int, dto: ChangePasswordDTO) -> None:
        if not self.repository.check_password(user_id, dto.old_password):
            raise ValidationAppError('Current password is incorrect')
        try:
            self.repository.validate_new_password(user_id, dto.new_password)
        except ValueError as exc:
            raise ValidationAppError(str(exc)) from exc
        try:
            self.repository.update(user_id, {'password': dto.new_password})
        except Exception as exc:
            from apps.accounts.infrastructure.models import User

            if isinstance(exc, User.DoesNotExist):
                raise NotFoundAppError('User not found') from None
            raise

    def forgot_password(self, email: str) -> None:
        profile = self.repository.get_by_email(email)
        if profile is None:
            return

        uid, token = self.repository.build_password_reset_token(profile.id)
        base_url = getattr(settings, 'SITE_BASE_URL', 'http://127.0.0.1:8000').rstrip('/')
        reset_url = f'{base_url}/accounts/password-reset/confirm/{uid}/{token}/'
        site_name = getattr(settings, 'SITE_NAME', 'ReportFlow')
        subject = f'{site_name} password reset'
        message = (
            f'You asked to reset your password for {site_name}.\n\n'
            f'Open this link to set a new password:\n{reset_url}\n\n'
            f'After saving, sign in at {base_url}/accounts/login/\n\n'
            f'If you did not request this, ignore this email.'
        )
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [profile.email],
            fail_silently=False,
        )

    def reset_password(self, uid: str, token: str, new_password: str) -> UserProfile:
        try:
            return self.repository.reset_password_with_token(uid, token, new_password)
        except Exception as exc:
            from apps.accounts.infrastructure.models import User

            if isinstance(exc, User.DoesNotExist):
                raise ValidationAppError('Invalid or expired reset link') from None
            if isinstance(exc, ValueError):
                raise ValidationAppError(str(exc)) from exc
            raise
