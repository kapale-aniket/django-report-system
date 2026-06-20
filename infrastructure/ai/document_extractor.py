"""Extract text from submitted report files (PDF or DOCX)."""
from __future__ import annotations

import logging
import zipfile
import xml.etree.ElementTree as ET

from apps.reports.constants import report_file_extension
from infrastructure.ai.pdf_extractor import extract_pdf_text

logger = logging.getLogger('reportflow.ai')

DOCX_WORD_NS = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def extract_docx_text(file_path: str, max_chars: int | None = None) -> dict:
    """Return text from a DOCX file using stdlib zip + XML parsing."""
    parts: list[str] = []
    try:
        with zipfile.ZipFile(file_path) as archive:
            xml_bytes = archive.read('word/document.xml')
    except (KeyError, zipfile.BadZipFile, OSError) as exc:
        logger.warning('DOCX text extraction failed for %s: %s', file_path, exc)
        return {
            'text': '',
            'page_count': 0,
            'char_count': 0,
            'method': 'docx',
            'error': str(exc),
        }

    root = ET.fromstring(xml_bytes)
    for node in root.iter(f'{DOCX_WORD_NS}t'):
        if node.text:
            parts.append(node.text)
        if node.tail:
            parts.append(node.tail)

    text = ' '.join(parts).strip()
    if max_chars and len(text) > max_chars:
        text = text[:max_chars]

    return {
        'text': text,
        'page_count': 1,
        'char_count': len(text),
        'method': 'docx',
    }


def extract_report_text(file_path: str, max_chars: int | None = None) -> dict:
    """Route to PDF or DOCX extractor based on file extension."""
    ext = report_file_extension(file_path)
    if ext == 'docx':
        return extract_docx_text(file_path, max_chars=max_chars)
    if ext == 'pdf':
        return extract_pdf_text(file_path, max_chars=max_chars)
    raise ValueError(f'Unsupported report file type: {ext or "unknown"}')
