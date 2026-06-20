"""Certificate achievement celebration for students."""
from __future__ import annotations

from django.db.models import Q
from django.urls import reverse

from apps.reports.infrastructure.models import CertificateCelebrationAcknowledgment, Report


def get_pending_certificate_celebration(user) -> dict | None:
    """
    Return the most recent certificate the student has not yet celebrated,
    or None if there is nothing pending.
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return None

    acked_ids = CertificateCelebrationAcknowledgment.objects.filter(user=user).values_list(
        'report_id', flat=True
    )

    report = (
        Report.objects.filter(
            is_deleted=False,
            status=Report.Status.APPROVED,
            certificate_generated=True,
            is_final_submission=True,
        )
        .filter(Q(student=user) | Q(group__members=user))
        .exclude(pk__in=acked_ids)
        .select_related('group')
        .distinct()
        .order_by('-updated_at')
        .first()
    )
    if report is None:
        return None

    return {
        'report_id': report.pk,
        'title': report.title,
        'marks': report.marks,
        'is_group': bool(report.group_id),
        'group_name': report.group.name if report.group_id else '',
        'download_url': reverse('reports:certificate', kwargs={'pk': report.pk}),
        'ack_url': reverse('reports:certificate_celebration_ack', kwargs={'pk': report.pk}),
    }


def acknowledge_certificate_celebration(user, report) -> None:
    CertificateCelebrationAcknowledgment.objects.get_or_create(user=user, report=report)
