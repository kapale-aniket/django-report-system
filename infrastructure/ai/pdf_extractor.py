"""Extract selectable text from PDF files."""
from __future__ import annotations

import logging

logger = logging.getLogger('reportflow.ai')


def extract_pdf_text(file_path: str, max_chars: int | None = None) -> dict:
    """
    Return native PDF text using PyMuPDF.
    Keys: text, page_count, char_count, method
    """
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError('PyMuPDF is required for PDF text extraction.') from exc

    doc = fitz.open(file_path)
    parts: list[str] = []
    try:
        for page in doc:
            parts.append(page.get_text('text') or '')
    finally:
        doc.close()

    text = '\n'.join(parts).strip()
    if max_chars and len(text) > max_chars:
        text = text[:max_chars]

    return {
        'text': text,
        'page_count': len(parts),
        'char_count': len(text),
        'method': 'native',
    }
