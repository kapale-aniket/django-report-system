from typing import Any

from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.infrastructure.models import User
from core.repositories.base import BaseRepository
from domain.accounts.entities import UserProfile


class UserRepository(BaseRepository[User]):
    """User persistence — all ORM access for accounts module."""

    model_class = User

    def _to_entity(self, user: User) -> UserProfile:
        return UserProfile(
            id=user.pk,
            username=user.username,
            email=user.email or '',
            role=user.role,
            department=user.department or '',
            roll_number=user.roll_number or '',
            is_active=user.is_active,
        )

    def _get_model(self, id: int) -> User | None:
        return super().get_by_id(id)

    def get_by_id(self, id: int) -> UserProfile | None:
        user = self._get_model(id)
        return self._to_entity(user) if user else None

    def get_by_username(self, username: str) -> UserProfile | None:
        user = self.first(username=username)
        return self._to_entity(user) if user else None

    def get_by_email(self, email: str) -> UserProfile | None:
        user = self.first(email__iexact=email)
        return self._to_entity(user) if user else None

    def create(self, data: dict[str, Any]) -> UserProfile:
        password = data.pop('password', None)
        user = self.model_class(**data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        user.refresh_from_db()
        return self._to_entity(user)

    def update(self, id: int, data: dict[str, Any]) -> UserProfile:
        user = self._get_model(id)
        if user is None:
            raise User.DoesNotExist
        password = data.pop('password', None)
        for key, value in data.items():
            setattr(user, key, value)
        if password:
            user.set_password(password)
        user.save()
        user.refresh_from_db()
        return self._to_entity(user)

    def delete(self, id: int) -> None:
        user = self._get_model(id)
        if user is None:
            raise User.DoesNotExist
        user.delete()

    def filter_by_role(self, role: str) -> list[UserProfile]:
        return [self._to_entity(u) for u in self.filter(role=role).order_by('username')]

    def authenticate(self, username: str, password: str) -> UserProfile | None:
        user = authenticate(username=username, password=password)
        if user is None:
            return None
        return self._to_entity(user)

    def check_password(self, user_id: int, password: str) -> bool:
        user = self._get_model(user_id)
        if user is None:
            return False
        return user.check_password(password)

    def issue_jwt_tokens(self, user_id: int) -> dict[str, str]:
        user = self._get_model(user_id)
        if user is None:
            raise User.DoesNotExist
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

    def blacklist_refresh_token(self, refresh_token: str) -> None:
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            pass

    def username_exists(self, username: str) -> bool:
        return self.exists(username=username)

    def email_exists(self, email: str, *, exclude_id: int | None = None) -> bool:
        qs = self.filter(email__iexact=email)
        if exclude_id is not None:
            qs = qs.exclude(pk=exclude_id)
        return qs.exists()

    def list_users(
        self,
        *,
        role: str | None = None,
        search: str = '',
        exclude_roles: list[str] | None = None,
    ) -> list[UserProfile]:
        qs = self.get_queryset()
        if exclude_roles:
            qs = qs.exclude(role__in=exclude_roles)
        if role:
            qs = qs.filter(role=role)
        if search:
            qs = qs.filter(
                Q(username__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
            )
        return [self._to_entity(u) for u in qs.order_by('role', 'username')]

    def pending_students_for_teacher(self, teacher_id: int) -> list[UserProfile]:
        qs = self.filter(
            role=User.Role.STUDENT,
            assigned_teacher_id=teacher_id,
            is_active=False,
        ).order_by('username')
        return [self._to_entity(u) for u in qs]

    def students_for_teacher(self, teacher_id: int) -> list[dict]:
        teacher = self._get_model(teacher_id)
        if teacher is None or teacher.role != User.Role.TEACHER:
            raise User.DoesNotExist

        students = self.filter(role=User.Role.STUDENT, assigned_teacher_id=teacher_id).order_by('username')
        return [
            {
                'id': student.pk,
                'username': student.username,
                'full_name': student.get_full_name() or student.username,
                'email': student.email or '',
                'department': student.department or '',
                'roll_number': student.roll_number or '',
                'is_active': student.is_active,
            }
            for student in students
        ]

    def get_user_detail(self, user_id: int) -> dict | None:
        user = self._get_model(user_id)
        if user is None:
            return None
        profile = self._to_entity(user)
        data = profile.to_dict()
        data['first_name'] = user.first_name
        data['last_name'] = user.last_name
        data['assigned_teacher_id'] = user.assigned_teacher_id
        data['profile_photo'] = user.profile_photo.url if user.profile_photo else ''
        return data

    def get_profile_detail(self, user_id: int) -> dict | None:
        return self.get_user_detail(user_id)

    def update_profile_photo(self, user_id: int, photo) -> UserProfile:
        user = self._get_model(user_id)
        if user is None:
            raise User.DoesNotExist
        if user.profile_photo:
            user.profile_photo.delete(save=False)
        user.profile_photo = photo
        user.save(update_fields=['profile_photo'])
        return self._to_entity(user)

    def assign_teacher(self, student_id: int, teacher_id: int | None) -> UserProfile:
        user = self._get_model(student_id)
        if user is None:
            raise User.DoesNotExist
        if teacher_id is None:
            user.assigned_teacher = None
        else:
            teacher = self._get_model(teacher_id)
            if teacher is None or teacher.role != User.Role.TEACHER:
                raise User.DoesNotExist
            user.assigned_teacher = teacher
        user.save(update_fields=['assigned_teacher'])
        return self._to_entity(user)

    def validate_new_password(self, user_id: int, password: str) -> None:
        user = self._get_model(user_id)
        if user is None:
            raise User.DoesNotExist
        validate_password(password, user)

    def build_password_reset_token(self, user_id: int) -> tuple[str, str]:
        user = self._get_model(user_id)
        if user is None:
            raise User.DoesNotExist
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        return uid, token

    def reset_password_with_token(self, uid: str, token: str, new_password: str) -> UserProfile:
        try:
            user_id = int(urlsafe_base64_decode(uid).decode())
        except (TypeError, ValueError, UnicodeDecodeError) as exc:
            raise User.DoesNotExist from exc
        user = self._get_model(user_id)
        if user is None or not default_token_generator.check_token(user, token):
            raise User.DoesNotExist
        try:
            validate_password(new_password, user)
        except DjangoValidationError as exc:
            raise ValueError('; '.join(exc.messages)) from exc
        user.set_password(new_password)
        user.save(update_fields=['password'])
        return self._to_entity(user)

    def list_teachers(self, active_only: bool = True) -> list[UserProfile]:
        qs = self.filter(role=User.Role.TEACHER)
        if active_only:
            qs = qs.filter(is_active=True)
        return [self._to_entity(u) for u in qs.order_by('username')]

    def list_teachers_by_department(self, department: str, *, active_only: bool = True) -> list[UserProfile]:
        cleaned = (department or '').strip()
        if not cleaned:
            return []
        qs = self.filter(role=User.Role.TEACHER, department__iexact=cleaned)
        if active_only:
            qs = qs.filter(is_active=True)
        return [self._to_entity(u) for u in qs.order_by('username')]
