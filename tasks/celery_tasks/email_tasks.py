"""Async email delivery."""
from celery import shared_task


@shared_task(name='reportflow.send_rejection_email')
def send_rejection_email_task(report_id: int, reason: str) -> None:
    from apps.reports.infrastructure.models import Report
    from infrastructure.email.smtp_sender import send_rejection_email

    report = Report.objects.select_related('student').filter(pk=report_id).first()
    if report is None:
        return
    send_rejection_email(report, reason)


@shared_task(name='reportflow.send_certificate_email')
def send_certificate_email_task(report_id: int) -> None:
    from apps.reports.infrastructure.models import Report
    from application.services.certificate_service import CertificateService
    from infrastructure.email.report_status_emails import send_admin_final_approval_email

    report = (
        Report.objects.select_related('student', 'student__assigned_teacher', 'rubric', 'group')
        .prefetch_related('group__members')
        .filter(pk=report_id)
        .first()
    )
    if report is None or not report.is_certificate_eligible:
        return

    service = CertificateService()
    for recipient in service.certificate_recipients(report):
        pdf_bytes = service.build_pdf_bytes(report, recipient=recipient)
        send_admin_final_approval_email(report, pdf_bytes=pdf_bytes, recipient=recipient)


@shared_task(name='reportflow.send_report_submitted_email')
def send_report_submitted_email_task(report_id: int) -> None:
    from apps.reports.infrastructure.models import Report
    from infrastructure.email.report_status_emails import send_report_submitted_email

    report = (
        Report.objects.select_related(
            'student',
            'student__assigned_teacher',
            'assigned_teacher',
            'group',
            'group__assigned_teacher',
        )
        .filter(pk=report_id)
        .first()
    )
    if report is None:
        return
    send_report_submitted_email(report)


@shared_task(name='reportflow.send_teacher_approved_email')
def send_teacher_approved_email_task(report_id: int) -> None:
    from apps.reports.infrastructure.models import Report
    from infrastructure.email.report_status_emails import send_teacher_approved_email

    report = (
        Report.objects.select_related(
            'student',
            'student__assigned_teacher',
            'assigned_teacher',
            'group',
            'group__assigned_teacher',
        )
        .filter(pk=report_id)
        .first()
    )
    if report is None:
        return
    send_teacher_approved_email(report)


@shared_task(name='reportflow.send_admin_final_approval_email')
def send_admin_final_approval_email_task(report_id: int) -> None:
    from apps.reports.infrastructure.models import Report
    from infrastructure.email.report_status_emails import send_admin_final_approval_email

    report = (
        Report.objects.select_related(
            'student',
            'student__assigned_teacher',
            'assigned_teacher',
            'group',
            'group__assigned_teacher',
        )
        .filter(pk=report_id)
        .first()
    )
    if report is None:
        return
    send_admin_final_approval_email(report)


@shared_task(name='reportflow.send_teacher_final_approval_email')
def send_teacher_final_approval_email_task(report_id: int) -> None:
    from apps.reports.infrastructure.models import Report
    from infrastructure.email.report_status_emails import send_teacher_final_approval_email

    report = (
        Report.objects.select_related(
            'student',
            'student__assigned_teacher',
            'assigned_teacher',
            'group',
            'group__assigned_teacher',
        )
        .filter(pk=report_id)
        .first()
    )
    if report is None:
        return
    send_teacher_final_approval_email(report)
