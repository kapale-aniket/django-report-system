from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q


class Department(models.Model):
    """College departments available when creating students and teachers."""

    name = models.CharField(max_length=120, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class User(AbstractUser):
    """
    Extended user with college role, department, and optional teacher assignment (students).
    """

    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        TEACHER = 'teacher', 'Teacher'
        STUDENT = 'student', 'Student'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
        db_index=True,
    )
    department = models.CharField(max_length=120, blank=True, db_index=True)
    roll_number = models.CharField(
        max_length=32,
        blank=True,
        unique=True,
        null=True,
        db_index=True,
        help_text='Auto-generated for students: DEPT + year + sequence.',
    )
    assigned_teacher = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_students',
        limit_choices_to=Q(role=Role.TEACHER),
    )
    profile_photo = models.ImageField(
        upload_to='profile_photos/%Y/%m/',
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ['username']

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'
