"""Email notifications for report workflow milestones."""
from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import EmailMessage

from apps.reports.teacher_helpers import get_report_assigned_teacher
from infrastructure.email.smtp_sender import _deliver_plain_email, _smtp_connection

logger = logging.getLogger('reportflow.email')


def _site_name() -> str:
    return getattr(settings, 'SITE_NAME', 'ReportFlow')


def _report_link(report) -> str:
    site_base_url = getattr(settings, 'SITE_BASE_URL', 'http://127.0.0.1:8000').rstrip('/')
    return f'{site_base_url}/reports/{report.pk}/'


def _display_name(user) -> str:
    return user.get_full_name() or user.username


def _from_email() -> str:
    return getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER)


def send_report_submitted_email(report) -> None:
    """Notify the assigned teacher when a student submits or resubmits."""
    teacher = get_report_assigned_teacher(report)
    if teacher is None or not teacher.email:
        return

    student_name = _display_name(report.student)
    teacher_label = _display_name(teacher)
    teacher_dept = (getattr(teacher, 'department', None) or '').strip()
    group_line = ''
    if report.group_id and getattr(report, 'group', None):
        group_line = f'Group: {report.group.name}\n'
    dept_line = f'Department: {teacher_dept}\n' if teacher_dept else ''
    try:
        _deliver_plain_email(
            subject=f'New report submitted — {report.title}',
            message=(
                f'Hello {teacher_label},\n\n'
                f'{student_name} submitted the project report "{report.title}".\n'
                f'{group_line}'
                f'{dept_line}\n'
                f'Please sign in to ReportFlow to review and score the submission.\n'
                f'Report link: {_report_link(report)}\n\n'
                f'— {_site_name()}'
            ),
            to_email=teacher.email,
        )
    except Exception:
        logger.exception('Failed to send submission email for report %s', report.pk)


def send_teacher_approved_email(report) -> None:
    """Notify the student after teacher approval."""
    student = report.student
    if not student.email:
        return

    teacher = get_report_assigned_teacher(report)
    teacher_name = _display_name(teacher) if teacher else 'your faculty guide'
    marks_line = ''
    if report.teacher_marks is not None:
        marks_line = f'Teacher score: {report.teacher_marks}/100\n'

    final_note = ''
    if report.is_final_submission:
        final_note = 'This was marked as the final submission and is now awaiting admin approval.\n'
    else:
        final_note = 'It is now awaiting admin final approval.\n'

    try:
        _deliver_plain_email(
            subject=f'Teacher approved your report — {report.title}',
            message=(
                f'Dear {_display_name(student)},\n\n'
                f'Good news! {teacher_name} has approved your project report "{report.title}".\n\n'
                f'{marks_line}'
                f'{final_note}\n'
                f'View your report: {_report_link(report)}\n\n'
                f'— {_site_name()}'
            ),
            to_email=student.email,
        )
    except Exception:
        logger.exception('Failed to send teacher-approved email for report %s', report.pk)


def send_admin_final_approval_email(report, *, pdf_bytes: bytes | None = None, recipient=None) -> None:
    """Notify a student when admin gives final approval. Attach certificate PDF when provided."""
    recipient = recipient or report.student
    if not recipient or not recipient.email:
        return

    marks_line = f'Final score: {report.marks}/100\n' if report.marks is not None else ''
    teacher_line = ''
    if report.teacher_marks is not None:
        teacher_line = f'Teacher score: {report.teacher_marks}/100\n'

    if pdf_bytes:
        intro = (
            f'Congratulations! Your project "{report.title}" has been fully approved.\n\n'
            f'{marks_line}{teacher_line}\n'
            f'Your official completion certificate is attached as a PDF with your name on it. '
            f'You can also download it anytime from the report page.\n\n'
            f'Report link: {_report_link(report)}\n'
        )
        subject = f'Project approved — certificate attached — {report.title}'
    else:
        intro = (
            f'Your project "{report.title}" has received final approval from the administration.\n\n'
            f'{marks_line}{teacher_line}\n'
            f'View your approved report: {_report_link(report)}\n'
        )
        subject = f'Project finally approved — {report.title}'

    body = f'Dear {_display_name(recipient)},\n\n{intro}\n— {_site_name()}'

    try:
        if pdf_bytes:
            safe_name = (_display_name(recipient) or recipient.username or 'student').replace(' ', '_')
            msg = EmailMessage(
                subject=subject,
                body=body,
                from_email=_from_email(),
                to=[recipient.email],
                connection=_smtp_connection(),
            )
            msg.attach(f'{safe_name}_project_certificate.pdf', pdf_bytes, 'application/pdf')
            msg.send(fail_silently=False)
        else:
            _deliver_plain_email(subject=subject, message=body, to_email=recipient.email)
    except Exception:
        logger.exception('Failed to send final approval email for report %s to %s', report.pk, recipient.pk)


def send_teacher_final_approval_email(report) -> None:
    """Notify the assigned teacher when admin finalizes approval."""
    teacher = get_report_assigned_teacher(report)
    if teacher is None or not teacher.email:
        return

    student_name = _display_name(report.student)
    marks_line = f'Final score: {report.marks}/100\n' if report.marks is not None else ''

    try:
        _deliver_plain_email(
            subject=f'Final approval completed — {report.title}',
            message=(
                f'Hello {_display_name(teacher)},\n\n'
                f'The project report "{report.title}" submitted by {student_name} '
                f'has received final administrative approval.\n\n'
                f'{marks_line}\n'
                f'Report link: {_report_link(report)}\n\n'
                f'— {_site_name()}'
            ),
            to_email=teacher.email,
        )
    except Exception:
        logger.exception('Failed to send teacher final-approval email for report %s', report.pk)
