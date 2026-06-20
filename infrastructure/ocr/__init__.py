"""OCR verification for submitted PDFs."""
from infrastructure.ocr.pdf_ocr import extract_ocr_text, verify_pdf_text

__all__ = ['extract_ocr_text', 'verify_pdf_text']
