"""Import specific team users with roles and departments."""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.infrastructure.models import Department, User

PASSWORD = 'ram123'

USER_PROFILES = {
    'Aniket': {
        'first_name': 'Aniket',
        'last_name': 'Kapale',
        'email': 'aniketkapale2002@gmail.com',
    },
    'Aniket1': {
        'first_name': 'Aniket',
        'last_name': 'Kapale',
        'email': 'aniketkapale75@gmail.com',
    },
    'Aniket2': {
        'first_name': 'Aniket',
        'last_name': '',
        'email': 'itsaniket340@gmail.com',
    },
    'Aniket3': {
        'first_name': 'Aniket',
        'last_name': 'Kapale',
        'email': 'aniketkapale512002@gmail.com',
    },
    'Aniket4': {
        'first_name': 'Aniket',
        'last_name': 'Kapale',
        'email': 'backendbyaniket@gmail.com',
    },
    'Aniket5': {
        'first_name': 'Aniket',
        'last_name': '',
        'email': 'aniketkapale02@gmail.com',
    },
    'Dhanashri': {
        'first_name': 'Dhanashri',
        'last_name': 'Dhekal',
        'email': 'dhanashridhekale2001@gmail.com',
    },
    'Rashmi': {
        'first_name': 'Rashmi',
        'last_name': '',
        'email': 'rashmipatil160599@gmail.com',
    },
    'Rashmi1': {
        'first_name': 'Rashmi',
        'last_name': 'Patil',
        'email': 'rashmipatil200118@gmail.com',
    },
}

# username, role, department
ASSIGNMENTS = [
    ('Aniket', User.Role.STUDENT, 'Computer Science'),
    ('Aniket1', User.Role.STUDENT, 'Computer Science'),
    ('Aniket2', User.Role.STUDENT, 'Computer Science'),
    ('Aniket3', User.Role.STUDENT, 'Computer Science'),
    ('Aniket4', User.Role.STUDENT, 'Computer Science'),
    ('Dhanashri', User.Role.TEACHER, 'Computer Science'),
    ('Rashmi', User.Role.TEACHER, 'Computer Science'),
    ('Aniket5', User.Role.STUDENT, 'Mechanical'),
    ('Rashmi1', User.Role.TEACHER, 'Civil'),
]


class Command(BaseCommand):
    help = 'Create/update team users with roles and departments.'

    def handle(self, *args, **options):
        departments = {name for _, _, name in ASSIGNMENTS}
        for name in sorted(departments):
            Department.objects.get_or_create(name=name, defaults={'is_active': True})

        with transaction.atomic():
            for username, role, department in ASSIGNMENTS:
                profile = USER_PROFILES[username]
                user, created = User.objects.update_or_create(
                    username=username,
                    defaults={
                        'email': profile['email'],
                        'first_name': profile['first_name'],
                        'last_name': profile['last_name'],
                        'role': role,
                        'department': department,
                        'is_active': True,
                        'is_staff': role == User.Role.ADMIN,
                    },
                )
                user.set_password(PASSWORD)
                user.save()
                action = 'Created' if created else 'Updated'
                self.stdout.write(
                    self.style.SUCCESS(
                        f'{action} {username} — {role} — {department} ({profile["email"]})'
                    )
                )

        self.stdout.write(self.style.SUCCESS(f'\nDefault password for all accounts: {PASSWORD}'))
