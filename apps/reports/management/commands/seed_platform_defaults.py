"""Seed status badge metadata (in code) and default evaluation rubric."""
from django.core.management.base import BaseCommand

from apps.reports.infrastructure.models import Rubric


class Command(BaseCommand):
    help = 'Seed default evaluation rubric with JSON criteria.'

    def handle(self, *args, **options):
        criteria = [
            {'id': 1, 'name': 'Documentation', 'max_score': 30, 'sort_order': 0},
            {'id': 2, 'name': 'Technical / Logic', 'max_score': 40, 'sort_order': 1},
            {'id': 3, 'name': 'Presentation & UI', 'max_score': 30, 'sort_order': 2},
        ]
        rubric, _ = Rubric.objects.update_or_create(
            name='Default project rubric',
            defaults={
                'is_default': True,
                'is_active': True,
                'criteria_json': criteria,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(f'Default rubric pk={rubric.pk} with {len(criteria)} criteria (JSON).')
        )

        from apps.reports.infrastructure.models import CertificateTemplate

        template, created = CertificateTemplate.objects.get_or_create(
            is_active=True,
            defaults={'name': 'Default ReportFlow certificate'},
        )
        action = 'Created' if created else 'Using existing'
        self.stdout.write(self.style.SUCCESS(f'{action} active certificate template pk={template.pk}.'))
