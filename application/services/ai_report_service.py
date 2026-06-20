"""AI-powered report document analysis for teachers."""
from __future__ import annotations

import json
import logging
from typing import Any

from django.conf import settings
from django.utils import timezone

from apps.reports.constants import report_file_extension
from apps.reports.infrastructure.models import Report
from application.services.report_service import ReportService
from core.exceptions.base import BusinessLogicError, NotFoundAppError, PermissionAppError
from core.services.base import BaseService
from infrastructure.ai.document_extractor import extract_report_text
from infrastructure.ai.llm_client import LLMClient, heuristic_qa_reply
from infrastructure.ai.report_heuristics import heuristic_report_analysis, is_legacy_placeholder_analysis
from infrastructure.ocr.pdf_ocr import extract_ocr_text, verify_pdf_text

logger = logging.getLogger('reportflow.ai')


class AIReportService(BaseService):
    """Extract report text, run OCR verification (PDF), and generate review suggestions."""

    def __init__(self, report_service: ReportService | None = None):
        self.report_service = report_service or ReportService()
        self.llm = LLMClient()

    def analyze_report_pdf(self, report_id: int) -> Report:
        if not getattr(settings, 'AI_FEATURES_ENABLED', True):
            raise BusinessLogicError('AI features are disabled.')

        report = Report.objects.select_related('rubric', 'student').filter(pk=report_id).first()
        if report is None:
            raise NotFoundAppError('Report not found')
        if not report.file:
            raise BusinessLogicError('Report has no file attached.')

        report.ai_processing_status = Report.AIProcessingStatus.PROCESSING
        report.save(update_fields=['ai_processing_status'])

        try:
            file_path = report.file.path
            max_chars = getattr(settings, 'AI_MAX_PDF_TEXT_CHARS', 12000)
            min_native = getattr(settings, 'AI_OCR_MIN_NATIVE_CHARS', 400)
            file_ext = report_file_extension(report.file.name)

            native = extract_report_text(file_path, max_chars=max_chars)
            native_text = native.get('text', '')

            ocr_text = ''
            verification: dict[str, Any]
            if file_ext == 'pdf':
                ocr = extract_ocr_text(file_path, max_chars=max_chars)
                ocr_text = ocr.get('text', '')
                if native.get('char_count', 0) >= min_native and not ocr_text:
                    ocr_text = native_text
                verification = verify_pdf_text(
                    native_text,
                    ocr_text,
                    native.get('page_count', 0),
                    min_native,
                )
                verification['processed_at'] = timezone.now().isoformat()
                verification['ocr_available'] = ocr.get('available', False)
            else:
                verification = {
                    'verified': True,
                    'method': native.get('method', file_ext),
                    'note': 'OCR verification applies to PDF uploads only.',
                    'processed_at': timezone.now().isoformat(),
                    'ocr_available': False,
                }

            criteria = report.rubric.get_criteria() if report.rubric_id else []
            analysis = self._build_analysis(report.title, native_text or ocr_text, criteria)
            analysis['generated_at'] = timezone.now().isoformat()

            report.extracted_text = native_text or ocr_text
            report.ocr_verification_json = verification
            report.ai_analysis_json = analysis
            report.ai_processing_status = Report.AIProcessingStatus.COMPLETED
            report.save(
                update_fields=[
                    'extracted_text',
                    'ocr_verification_json',
                    'ai_analysis_json',
                    'ai_processing_status',
                ]
            )
            return report
        except Exception as exc:
            logger.exception('AI report processing failed for report %s', report_id)
            report.ai_processing_status = Report.AIProcessingStatus.FAILED
            report.ai_analysis_json = {
                'error': str(exc),
                'generated_at': timezone.now().isoformat(),
            }
            report.save(update_fields=['ai_processing_status', 'ai_analysis_json'])
            raise

    def _build_analysis(self, title: str, text: str, criteria: list[dict]) -> dict[str, Any]:
        if self.llm.is_configured() and text.strip():
            criteria_payload = [
                {
                    'id': row.get('id'),
                    'name': row.get('name'),
                    'max_score': row.get('max_score'),
                }
                for row in criteria
            ]
            system_prompt = (
                'You assist college teachers reviewing student project reports (PDF or DOCX). '
                'Return strict JSON with keys: summary, suggested_criterion_scores, '
                'suggested_feedback, suggested_teacher_marks. '
                'suggested_criterion_scores must map criterion id strings to integer scores '
                'within each max_score. suggested_teacher_marks is 0-100. '
                'Be concise and professional.'
            )
            user_prompt = json.dumps(
                {
                    'report_title': title,
                    'rubric_criteria': criteria_payload,
                    'extracted_text': text[:10000],
                },
                ensure_ascii=False,
            )
            payload = self.llm.chat_json(system_prompt, user_prompt)
            if payload:
                scores = payload.get('suggested_criterion_scores') or {}
                normalized_scores = {str(k): int(v) for k, v in scores.items()}
                return {
                    'summary': payload.get('summary', ''),
                    'suggested_criterion_scores': normalized_scores,
                    'suggested_feedback': payload.get('suggested_feedback', ''),
                    'suggested_teacher_marks': int(payload.get('suggested_teacher_marks') or 0),
                    'provider': 'openai',
                }

        return heuristic_report_analysis(title, text, criteria)

    def get_teacher_insights(self, user, report_id: int) -> dict[str, Any]:
        report = self.report_service._get_report_or_404(report_id)
        self.report_service._ensure_view_access(user, report)

        role = getattr(user, 'role', None)
        if role not in ('teacher', 'admin'):
            raise PermissionAppError('Only teachers and admins can view AI insights.')

        if report.ai_processing_status == Report.AIProcessingStatus.PENDING:
            self.analyze_report_pdf(report_id)
            report.refresh_from_db()
        elif report.ai_processing_status == Report.AIProcessingStatus.COMPLETED:
            cached = report.ai_analysis_json or {}
            if is_legacy_placeholder_analysis(cached):
                self.analyze_report_pdf(report_id)
                report.refresh_from_db()

        analysis = report.ai_analysis_json or {}
        ocr = report.ocr_verification_json or {}
        criteria = report.rubric.get_criteria() if report.rubric_id else []

        return {
            'report_id': report.pk,
            'processing_status': report.ai_processing_status,
            'summary': analysis.get('summary', ''),
            'suggested_criterion_scores': analysis.get('suggested_criterion_scores', {}),
            'suggested_feedback': analysis.get('suggested_feedback', ''),
            'suggested_teacher_marks': analysis.get('suggested_teacher_marks'),
            'provider': analysis.get('provider', ''),
            'ocr_verification': ocr,
            'extracted_text_preview': (report.extracted_text or '')[:500],
            'rubric_criteria': criteria,
        }

    def apply_suggestions_to_form(self, user, report_id: int) -> dict[str, Any]:
        """Return suggestion payload for pre-filling teacher approve form."""
        payload = self.get_teacher_insights(user, report_id)
        return {
            'summary': payload.get('summary', ''),
            'criterion_scores': payload.get('suggested_criterion_scores', {}),
            'feedback': payload.get('suggested_feedback', ''),
            'teacher_marks': payload.get('suggested_teacher_marks'),
            'ocr_verification': payload.get('ocr_verification', {}),
            'processing_status': payload.get('processing_status', ''),
        }
