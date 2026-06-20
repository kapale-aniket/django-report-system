"""Per-report teacher assignment helpers."""
from __future__ import annotations

from django.db.models import Q

from apps.accounts.infrastructure.models import User


def get_report_assigned_teacher(report):
    if report is None:
        return None
    if getattr(report, 'assigned_teacher_id', None):
        return report.assigned_teacher
    student = getattr(report, 'student', None)
    if student is not None and student.assigned_teacher_id:
        return student.assigned_teacher
    return None


def get_report_assigned_teacher_id(report) -> int | None:
    teacher = get_report_assigned_teacher(report)
    return teacher.pk if teacher else None


def teacher_can_access_report(user, report) -> bool:
    teacher_id = get_report_assigned_teacher_id(report)
    return teacher_id is not None and teacher_id == getattr(user, 'id', None)


def reports_for_teacher_q(teacher) -> Q:
    """Match reports assigned to this teacher (per project), with student default fallback."""
    return Q(assigned_teacher=teacher) | Q(
        assigned_teacher__isnull=True,
        student__assigned_teacher=teacher,
    )
