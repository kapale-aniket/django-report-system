"""OCR extraction and verification for PDF submissions."""
from __future__ import annotations

import difflib
import logging
import re
from typing import Any

logger = logging.getLogger('reportflow.ai')


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _ocr_available() -> bool:
    try:
        import pytesseract  # noqa: F401
        return True
    except ImportError:
        return False


def extract_ocr_text(file_path: str, max_pages: int = 5, max_chars: int | None = None) -> dict:
    """
    OCR rendered PDF pages when native text is sparse.
    Returns text, page_count, char_count, method, available flag.
    """
    if not _ocr_available():
        return {'text': '', 'page_count': 0, 'char_count': 0, 'method': 'ocr', 'available': False}

    try:
        import fitz
        import pytesseract
        from django.conf import settings

        if getattr(settings, 'TESSERACT_CMD', ''):
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
    except ImportError:
        return {'text': '', 'page_count': 0, 'char_count': 0, 'method': 'ocr', 'available': False}

    doc = fitz.open(file_path)
    parts: list[str] = []
    try:
        limit = min(len(doc), max_pages)
        for index in range(limit):
            page = doc[index]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_bytes = pix.tobytes('png')
            try:
                from PIL import Image
                import io

                image = Image.open(io.BytesIO(img_bytes))
                text = pytesseract.image_to_string(image)
            except Exception as exc:
                logger.warning('OCR failed on page %s: %s', index + 1, exc)
                text = ''
            parts.append(text or '')
    finally:
        doc.close()

    text = '\n'.join(parts).strip()
    if max_chars and len(text) > max_chars:
        text = text[:max_chars]

    return {
        'text': text,
        'page_count': len(parts),
        'char_count': len(text),
        'method': 'ocr',
        'available': True,
    }


def verify_pdf_text(native_text: str, ocr_text: str, page_count: int, min_native_chars: int) -> dict[str, Any]:
    """Compare native vs OCR text and return verification metadata."""
    native_len = len((native_text or '').strip())
    ocr_len = len((ocr_text or '').strip())
    pages = max(page_count, 1)
    avg_native = native_len / pages

    flags: list[str] = []
    if native_len < min_native_chars:
        flags.append('low_native_text')
    if ocr_len == 0:
        flags.append('ocr_unavailable_or_empty')

    ratio = 0.0
    if native_text and ocr_text:
        ratio = difflib.SequenceMatcher(
            None,
            _normalize(native_text[:8000]),
            _normalize(ocr_text[:8000]),
        ).ratio()

    verified = native_len >= min_native_chars or ratio >= 0.45 or (ocr_len >= min_native_chars and ratio >= 0.3)
    confidence = 'high' if verified and ratio >= 0.6 else 'medium' if verified else 'low'

    return {
        'native_text_length': native_len,
        'ocr_text_length': ocr_len,
        'similarity_ratio': round(ratio, 3),
        'verified': verified,
        'confidence': confidence,
        'flags': flags,
        'page_count': page_count,
        'avg_native_chars_per_page': round(avg_native, 1),
    }
