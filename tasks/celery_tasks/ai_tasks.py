"""Async AI processing for submitted reports."""
from celery import shared_task


@shared_task(name='reportflow.process_report_ai')
def process_report_ai_task(report_id: int) -> None:
    from application.services.ai_report_service import AIReportService

    AIReportService().analyze_report_pdf(report_id)
