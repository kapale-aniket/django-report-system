"""
Delete all student and teacher accounts, their reports, and related data.
Admin accounts, system settings, rubrics, and FAQs are kept.

Usage:
  python manage.py purge_students_teachers
  python manage.py purge_students_teachers --dry-run
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from apps.accounts.infrastructure.models import User
from apps.messaging.infrastructure.models import Message
from apps.qa.infrastructure.models import QAItem
from apps.reports.infrastructure.models import (
    ActivityLog,
    Notification,
    ProjectGroup,
    Report,
    ReportRequest,
)


class Command(BaseCommand):
    help = 'Remove all students, teachers, their reports, groups, and related records. Admins are kept.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show counts only; do not delete anything.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        student_teacher_qs = User.objects.filter(role__in=[User.Role.STUDENT, User.Role.TEACHER])
        user_ids = list(student_teacher_qs.values_list('pk', flat=True))

        counts = {
            'reports': Report.objects.count(),
            'project_groups': ProjectGroup.objects.count(),
            'report_requests': ReportRequest.objects.count(),
            'activity_logs': ActivityLog.objects.count(),
            'notifications': Notification.objects.filter(user_id__in=user_ids).count(),
            'messages': Message.objects.filter(
                Q(sender_id__in=user_ids) | Q(receiver_id__in=user_ids)
            ).count(),
            'qa_user_items': QAItem.objects.filter(
                user_id__in=user_ids,
                qa_type=QAItem.QAType.USER,
            ).count(),
            'students': User.objects.filter(role=User.Role.STUDENT).count(),
            'teachers': User.objects.filter(role=User.Role.TEACHER).count(),
        }

        self.stdout.write('Will delete:')
        for label, value in counts.items():
            self.stdout.write(f'  {label}: {value}')

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run — no data deleted.'))
            return

        if not any(counts.values()):
            self.stdout.write(self.style.SUCCESS('Nothing to delete.'))
            return

        with transaction.atomic():
            ActivityLog.objects.all().delete()
            ReportRequest.objects.all().delete()
            Report.objects.all().delete()
            ProjectGroup.objects.all().delete()
            Notification.objects.filter(user_id__in=user_ids).delete()
            Message.objects.filter(Q(sender_id__in=user_ids) | Q(receiver_id__in=user_ids)).delete()
            QAItem.objects.filter(user_id__in=user_ids, qa_type=QAItem.QAType.USER).delete()
            deleted, detail = student_teacher_qs.delete()

        self.stdout.write(self.style.SUCCESS(f'Deleted {deleted} user-related row(s).'))
        if detail:
            for model_label, count in sorted(detail.items()):
                if count:
                    self.stdout.write(f'  {model_label}: {count}')
        self.stdout.write(self.style.SUCCESS('Admin accounts and system settings were kept.'))
