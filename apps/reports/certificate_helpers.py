"""Certificate issuance after full approval."""
import logging

from application.services.certificate_service import CertificateService
from apps.reports.group_helpers import notify_report_stakeholders
from tasks.dispatch import queue_certificate_email, queue_teacher_final_approval_email

logger = logging.getLogger('reportflow.certificates')


def issue_certificate_if_eligible(report) -> bool:
    """
    Generate and email the PDF certificate when the report is fully approved
    and the teacher marked it as the final submission.
    """
    if not report.is_certificate_eligible or report.certificate_generated:
        return False

    certificate_service = CertificateService()
    certificate_service.ensure_all_recipient_codes(report)

    report.certificate_generated = True
    report.save(update_fields=['certificate_generated'])

    try:
        queue_certificate_email(report.pk)
        queue_teacher_final_approval_email(report.pk)
        notify_report_stakeholders(
            report,
            f'Congratulations! Your project "{report.title}" is complete. '
            'Your personalized certificate (with your name) was emailed to you and is available on the report page.',
            link=f'/reports/{report.pk}/',
        )
    except Exception:
        logger.exception(
            'Certificate issued for report %s but delivery notification failed',
            report.pk,
        )
    return True


def notify_admin_final_approval(report) -> bool:
    """Send workflow emails after admin final approval."""
    from tasks.dispatch import queue_admin_final_approval_email

    certificate_issued = issue_certificate_if_eligible(report)
    if not certificate_issued:
        queue_admin_final_approval_email(report.pk)
        queue_teacher_final_approval_email(report.pk)
    return certificate_issued
