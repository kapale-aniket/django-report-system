"""PDF certificate generation — configurable layout with QR verification."""
from __future__ import annotations

import io
import secrets
import textwrap
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

import qrcode
from apps.reports.certificate_design import format_certificate_id, resolve_certificate_design
from apps.reports.teacher_helpers import get_report_assigned_teacher
from core.utils.certificate_urls import build_public_certificate_verify_url
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape, letter
from reportlab.lib.units import cm, mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

if TYPE_CHECKING:
    from apps.reports.infrastructure.models import CertificateTemplate

SITE_NAME = 'ReportFlow'


@dataclass(frozen=True)
class CertificateContext:
    student_name: str
    project_title: str
    department: str = ''
    roll_number: str = ''
    username: str = ''
    academic_year: str = ''
    group_name: str = ''
    teacher_name: str = ''
    teacher_marks: int | None = None
    final_marks: int | None = None
    rubric_score: int | None = None
    rubric_max: int | None = None
    completion_date: datetime | None = None
    submitted_date: datetime | None = None
    verification_code: str = ''
    verify_url: str = ''


def marks_to_grade(marks: int | None) -> tuple[str, str]:
    if marks is None:
        return ('—', 'Not graded')
    if marks >= 90:
        return ('A+', 'Outstanding')
    if marks >= 80:
        return ('A', 'Excellent')
    if marks >= 70:
        return ('B+', 'Very Good')
    if marks >= 60:
        return ('B', 'Good')
    if marks >= 50:
        return ('C', 'Satisfactory')
    if marks >= 40:
        return ('D', 'Pass')
    return ('F', 'Needs Improvement')


def certificate_context_from_report(
    report,
    *,
    verification_code: str,
    verify_url: str,
    recipient=None,
) -> CertificateContext:
    student = recipient or report.student
    teacher = get_report_assigned_teacher(report)
    completion = report.updated_at
    if completion and timezone.is_aware(completion):
        completion = timezone.localtime(completion)
    submitted = report.submitted_at
    if submitted and timezone.is_aware(submitted):
        submitted = timezone.localtime(submitted)
    group_name = ''
    if report.group_id:
        group = getattr(report, 'group', None)
        if group is not None:
            group_name = group.name or ''
    return CertificateContext(
        student_name=student.get_full_name() or student.username,
        project_title=report.title,
        department=getattr(student, 'department', '') or '',
        roll_number=getattr(student, 'roll_number', '') or '',
        username=student.username,
        academic_year=(report.academic_year or '').strip(),
        group_name=group_name,
        teacher_name=(teacher.get_full_name() or teacher.username) if teacher else '',
        teacher_marks=report.teacher_marks,
        final_marks=report.marks,
        completion_date=completion,
        submitted_date=submitted,
        verification_code=verification_code,
        verify_url=verify_url,
    )


def _resolve_image_path(image_field) -> str | None:
    import os

    if not image_field or not getattr(image_field, 'name', None):
        return None
    try:
        if hasattr(image_field, 'storage') and hasattr(image_field.storage, 'exists'):
            if not image_field.storage.exists(image_field.name):
                return None
        path = image_field.path
    except (ValueError, NotImplementedError, FileNotFoundError):
        return None
    return path if os.path.isfile(path) else None


def _resolve_reference_image_path(template: CertificateTemplate | None) -> str | None:
    if template is None:
        return None
    return _resolve_image_path(template.reference_image)


def _hex(value: str, fallback: str = '#2d5a47') -> colors.Color:
    raw = (value or fallback).strip()
    if not raw.startswith('#'):
        raw = f'#{raw}'
    try:
        return colors.HexColor(raw)
    except Exception:
        return colors.HexColor(fallback)


def _fmt_date(value: datetime | None) -> str:
    if not value:
        return timezone.localtime(timezone.now()).strftime('%B %d, %Y')
    return value.strftime('%B %d, %Y')


def _page_size_from_design(design: dict) -> tuple[float, float]:
    page = design.get('page', {})
    size_key = page.get('size', 'a4_landscape')
    if size_key == 'a4_portrait':
        return A4
    if size_key == 'letter':
        return landscape(letter)
    if size_key == 'custom':
        width = float(page.get('custom_width_mm', 297)) * mm
        height = float(page.get('custom_height_mm', 210)) * mm
        return (width, height)
    return landscape(A4)


def _draw_text_aligned(
    c: canvas.Canvas,
    x_center: float,
    y: float,
    text: str,
    font: str,
    size: int,
    color,
    alignment: str,
    content_left: float,
    content_right: float,
) -> None:
    c.setFont(font, size)
    c.setFillColor(color)
    text = text[:120]
    if alignment == 'left':
        c.drawString(content_left, y, text)
    elif alignment == 'right':
        width = c.stringWidth(text, font, size)
        c.drawString(content_right - width, y, text)
    else:
        c.drawCentredString(x_center, y, text)


def _open_image_source(image_field):
    """Return a path or readable file-like object for ReportLab/PIL."""
    if not image_field or not getattr(image_field, 'name', None):
        return None

    path = _resolve_image_path(image_field)
    if path:
        return path

    # In-memory upload (draft preview) — avoid touching FieldFile.read (opens storage).
    from django.core.files.uploadedfile import UploadedFile

    if isinstance(image_field, UploadedFile):
        try:
            image_field.seek(0)
            return image_field
        except (OSError, AttributeError, ValueError):
            return None

    try:
        return image_field.open('rb')
    except (ValueError, FileNotFoundError, OSError, AttributeError):
        return None


def _draw_background_image(c: canvas.Canvas, image_source, w: float, h: float, opacity: float = 1.0) -> None:
    from PIL import Image

    if not image_source:
        return
    try:
        with Image.open(image_source) as img:
            img_w, img_h = img.size
        scale = max(w / img_w, h / img_h)
        draw_w = img_w * scale
        draw_h = img_h * scale
        x = (w - draw_w) / 2
        y = (h - draw_h) / 2
        if hasattr(image_source, 'seek'):
            image_source.seek(0)
        if opacity < 1.0:
            c.saveState()
            c.setFillAlpha(opacity)
        c.drawImage(ImageReader(image_source), x, y, width=draw_w, height=draw_h, mask='auto')
        if opacity < 1.0:
            c.restoreState()
    except (OSError, ValueError):
        return


def _draw_solid_background(c: canvas.Canvas, w: float, h: float, bg_color) -> None:
    c.setFillColor(bg_color)
    c.rect(0, 0, w, h, fill=1, stroke=0)


def _draw_gradient_background(c: canvas.Canvas, w: float, h: float, primary, secondary) -> None:
    steps = 24
    for index in range(steps):
        ratio = index / max(steps - 1, 1)
        r = primary.red + (secondary.red - primary.red) * ratio
        g = primary.green + (secondary.green - primary.green) * ratio
        b = primary.blue + (secondary.blue - primary.blue) * ratio
        c.setFillColor(colors.Color(r, g, b))
        band_h = h / steps
        c.rect(0, h - (index + 1) * band_h, w, band_h + 0.5, fill=1, stroke=0)


def _draw_image_overlay(c: canvas.Canvas, image_source, w: float, h: float, opacity: float, *, centered: bool = True) -> None:
    from PIL import Image

    if not image_source:
        return
    try:
        with Image.open(image_source) as img:
            img_w, img_h = img.size
        max_w, max_h = w * 0.35, h * 0.35
        scale = min(max_w / img_w, max_h / img_h, 1.0)
        draw_w = img_w * scale
        draw_h = img_h * scale
        x = (w - draw_w) / 2 if centered else w - draw_w - 1.2 * cm
        y = (h - draw_h) / 2 if centered else h - draw_h - 1.2 * cm
        if hasattr(image_source, 'seek'):
            image_source.seek(0)
        c.saveState()
        c.setFillAlpha(opacity)
        c.drawImage(ImageReader(image_source), x, y, width=draw_w, height=draw_h, mask='auto')
        c.restoreState()
    except (OSError, ValueError):
        return


def _draw_page_frame(
    c: canvas.Canvas,
    w: float,
    h: float,
    margin: float,
    design: dict,
    *,
    has_background: bool,
) -> None:
    border = design['border']
    palette = design['colors']
    inner_w = w - 2 * margin
    inner_h = h - 2 * margin
    accent = _hex(palette['primary'])
    secondary = _hex(palette['accent'])
    border_color = _hex(border.get('color') or palette['primary'])
    parchment = _hex(palette['background'])
    radius = float(border.get('radius', 12))
    line_w = float(border.get('width', 2.8))
    style = border.get('style', 'classic')

    if not has_background:
        mode = design['background'].get('mode', 'solid')
        if mode == 'gradient':
            _draw_gradient_background(c, w, h, accent, secondary)
        else:
            _draw_solid_background(c, w, h, parchment)

    panel_alpha = 0.88 if has_background else 1.0
    c.setFillColor(colors.Color(1, 1, 1, alpha=panel_alpha))
    c.roundRect(margin, margin, inner_w, inner_h, radius, fill=1, stroke=0)

    c.setStrokeColor(border_color)
    if style == 'minimal':
        c.setLineWidth(max(line_w * 0.5, 0.8))
        c.roundRect(margin, margin, inner_w, inner_h, radius, fill=0, stroke=1)
    elif style == 'modern':
        c.setLineWidth(line_w)
        c.roundRect(margin, margin, inner_w, inner_h, radius, fill=0, stroke=1)
    elif style == 'royal':
        c.setLineWidth(line_w + 1.2)
        c.roundRect(margin, margin, inner_w, inner_h, radius, fill=0, stroke=1)
        c.setStrokeColor(secondary)
        c.setLineWidth(1.4)
        c.roundRect(margin + 0.35 * cm, margin + 0.35 * cm, inner_w - 0.7 * cm, inner_h - 0.7 * cm, radius - 2, fill=0, stroke=1)
        accent_h = 0.65 * cm
        c.setFillColor(accent)
        c.roundRect(margin + 0.35 * cm, h - margin - accent_h - 0.35 * cm, inner_w - 0.7 * cm, accent_h, 5, fill=1, stroke=0)
    else:
        c.setLineWidth(line_w)
        c.roundRect(margin, margin, inner_w, inner_h, radius, fill=0, stroke=1)
        c.setStrokeColor(secondary)
        c.setLineWidth(1.1)
        c.roundRect(margin + 0.22 * cm, margin + 0.22 * cm, inner_w - 0.44 * cm, inner_h - 0.44 * cm, max(radius - 2, 4), fill=0, stroke=1)
        accent_h = 0.55 * cm
        c.setFillColor(accent)
        c.roundRect(margin + 0.22 * cm, h - margin - accent_h - 0.22 * cm, inner_w - 0.44 * cm, accent_h, 5, fill=1, stroke=0)


def _draw_corner_flourish(c: canvas.Canvas, x: float, y: float, size: float, quadrant: int, accent) -> None:
    sx = 1 if quadrant in (1, 2) else -1
    sy = 1 if quadrant in (1, 4) else -1
    c.setStrokeColor(accent)
    c.setLineWidth(2.2)
    c.line(x, y, x + sx * size, y)
    c.line(x, y, x, y + sy * size)


def _draw_award_seal(c: canvas.Canvas, cx: float, cy: float, radius: float, accent, secondary, label: str = 'RF') -> None:
    c.setFillColor(secondary)
    c.circle(cx, cy, radius + 0.08 * cm, fill=1, stroke=0)
    c.setFillColor(accent)
    c.circle(cx, cy, radius, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 8)
    c.drawCentredString(cx, cy + 0.08 * cm, label[:4].upper())
    c.setFont('Helvetica', 5.5)
    c.drawCentredString(cx, cy - 0.28 * cm, 'VERIFIED')


def _draw_ribbon(c: canvas.Canvas, cx: float, cy: float, accent) -> None:
    c.setFillColor(accent)
    c.rect(cx - 1.4 * cm, cy, 2.8 * cm, 0.35 * cm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 7)
    c.drawCentredString(cx, cy + 0.08 * cm, 'AWARD')


def _draw_centered_lines(
    c: canvas.Canvas,
    center_x: float,
    y_start: float,
    lines: list[str],
    font: str,
    size: int,
    color,
    leading: float | None = None,
) -> float:
    leading = leading or size + 5
    y_cursor = y_start
    for line in lines:
        c.setFont(font, size)
        c.setFillColor(color)
        c.drawCentredString(center_x, y_cursor, line)
        y_cursor -= leading
    return y_cursor


def _wrap_project_title(title: str, max_chars: int = 58, max_lines: int = 2) -> list[str]:
    wrapped = textwrap.wrap(title, width=max_chars)
    if len(wrapped) > max_lines:
        wrapped = textwrap.wrap(title, width=max_chars - 8)[:max_lines]
        if len(wrapped) == max_lines:
            wrapped[-1] = wrapped[-1][: max_chars - 3] + '…'
    return [f'"{line}"' for line in wrapped] if wrapped else ['"(Untitled project)"']


def _draw_score_chip(
    c: canvas.Canvas,
    x: float,
    y: float,
    width: float,
    height: float,
    label: str,
    value: str,
    accent,
    muted,
) -> None:
    c.setFillColor(colors.white)
    c.setStrokeColor(accent)
    c.setLineWidth(1.1)
    c.roundRect(x, y, width, height, 8, fill=1, stroke=1)
    c.setFont('Helvetica', 7.5)
    c.setFillColor(muted)
    label_width = c.stringWidth(label.upper(), 'Helvetica', 7.5)
    c.drawString(x + (width - label_width) / 2, y + height - 0.5 * cm, label.upper())
    c.setFont('Helvetica-Bold', 12)
    c.setFillColor(accent)
    value_display = value[:28]
    value_width = c.stringWidth(value_display, 'Helvetica-Bold', 12)
    c.drawString(x + (width - value_width) / 2, y + 0.38 * cm, value_display)


def _draw_qr_panel(c: canvas.Canvas, qr_buf: io.BytesIO, x: float, y: float, size: float, accent, secondary) -> None:
    panel_pad = 0.25 * cm
    panel_w = size + 2 * panel_pad
    panel_h = size + 1.1 * cm
    c.setFillColor(colors.white)
    c.setStrokeColor(secondary)
    c.setLineWidth(1.2)
    c.roundRect(x, y, panel_w, panel_h, 6, fill=1, stroke=1)
    c.drawImage(ImageReader(qr_buf), x + panel_pad, y + 0.55 * cm, width=size, height=size)
    c.setFont('Helvetica-Bold', 7)
    c.setFillColor(accent)
    c.drawCentredString(x + panel_w / 2, y + 0.22 * cm, 'Scan to verify')


def _draw_signature_row(
    c: canvas.Canvas,
    start_x: float,
    y: float,
    total_width: float,
    signatories: list[dict],
    muted,
    signature_image_source,
) -> None:
    count = max(len(signatories), 1)
    gap = 0.55 * cm
    line_w = (total_width - gap * (count - 1)) / count
    for index, signer in enumerate(signatories[:3]):
        sx = start_x + index * (line_w + gap)
        if signature_image_source and index == 0:
            try:
                if hasattr(signature_image_source, 'seek'):
                    signature_image_source.seek(0)
                c.drawImage(
                    ImageReader(signature_image_source),
                    sx + line_w * 0.25,
                    y + 0.15 * cm,
                    width=line_w * 0.5,
                    height=0.55 * cm,
                    mask='auto',
                )
            except (OSError, ValueError):
                pass
        c.setStrokeColor(muted)
        c.setLineWidth(0.7)
        c.line(sx, y, sx + line_w, y)
        c.setFont('Helvetica', 8)
        c.setFillColor(muted)
        label = signer.get('designation') or signer.get('name') or 'Signatory'
        c.drawCentredString(sx + line_w / 2, y - 0.42 * cm, label[:32])


def _draw_logo(c: canvas.Canvas, image_source, w: float, h: float, margin: float, position: str) -> None:
    from PIL import Image

    if not image_source:
        return
    try:
        with Image.open(image_source) as img:
            img_w, img_h = img.size
        logo_h = 1.1 * cm
        scale = logo_h / img_h
        logo_w = img_w * scale
        y = h - margin - logo_h - 0.35 * cm
        if position == 'top-center':
            x = (w - logo_w) / 2
        elif position == 'top-right':
            x = w - margin - logo_w - 0.2 * cm
        else:
            x = margin + 0.35 * cm
        if hasattr(image_source, 'seek'):
            image_source.seek(0)
        c.drawImage(ImageReader(image_source), x, y, width=logo_w, height=logo_h, mask='auto')
    except (OSError, ValueError):
        return


def build_certificate_pdf(
    student_display_name: str,
    project_title: str,
    *,
    department: str = '',
    teacher_marks: int | None = None,
    verification_code: str | None = None,
    verify_url: str | None = None,
    **extra,
) -> bytes:
    ctx = CertificateContext(
        student_name=student_display_name,
        project_title=project_title,
        department=department,
        teacher_marks=teacher_marks,
        verification_code=verification_code or secrets.token_urlsafe(12),
        verify_url=verify_url or '',
        **{k: v for k, v in extra.items() if k in CertificateContext.__dataclass_fields__},
    )
    return build_certificate_pdf_from_context(ctx)


def build_certificate_pdf_from_context(
    ctx: CertificateContext,
    template: CertificateTemplate | None = None,
) -> bytes:
    design = resolve_certificate_design(template)
    palette = design['colors']
    typography = design['typography']
    layout = design['layout']
    decorative = design['decorative']

    accent = _hex(palette['primary'])
    secondary = _hex(palette['accent'])
    ink = _hex(palette['text'])
    muted = _hex(palette['muted'])
    name_color = _hex(palette['name'])

    code = ctx.verification_code or secrets.token_urlsafe(12)
    url = ctx.verify_url or build_public_certificate_verify_url(code)
    cert_id = format_certificate_id(code, design, year=(ctx.academic_year or '')[:4] or None)
    letter, grade_label = marks_to_grade(ctx.teacher_marks or ctx.final_marks)
    completion_str = _fmt_date(ctx.completion_date)
    submitted_str = _fmt_date(ctx.submitted_date)

    page_size = _page_size_from_design(design)
    margin = float(layout.get('margin_cm', 1.05)) * cm
    padding = float(layout.get('padding_cm', 0.9)) * cm
    alignment = typography.get('text_alignment', 'center')

    qr_buf = None
    if design.get('qr', {}).get('enabled', True):
        qr = qrcode.QRCode(box_size=4, border=1)
        qr.add_data(url)
        qr.make(fit=True)
        qr_fill = palette['primary'] if str(palette['primary']).startswith('#') else f"#{palette['primary']}"
        qr_img = qr.make_image(fill_color=qr_fill, back_color='white')
        qr_buf = io.BytesIO()
        qr_img.save(qr_buf, format='PNG')
        qr_buf.seek(0)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=page_size)
    w, h = page_size
    qr_size = 2.45 * cm
    qr_panel_w = qr_size + 0.5 * cm
    qr_x = w - margin - qr_panel_w - 0.12 * cm if qr_buf else w - margin

    content_left = margin + padding
    content_right = (qr_x - 0.5 * cm) if qr_buf else (w - margin - padding)
    content_center_x = (content_left + content_right) / 2
    content_width = content_right - content_left

    bg_mode = design['background'].get('mode', 'solid')
    bg_opacity = float(design['background'].get('opacity', 1.0))
    bg_source = _open_image_source(template.reference_image) if template and template.reference_image else None
    use_image_bg = bool(
        bg_source
        and template
        and template.use_reference_background
        and bg_mode in ('image', 'texture')
    )
    if use_image_bg:
        _draw_background_image(c, bg_source, w, h, bg_opacity)
    elif bg_mode == 'image' and bg_source:
        _draw_background_image(c, bg_source, w, h, bg_opacity)

    _draw_page_frame(c, w, h, margin, design, has_background=use_image_bg or (bg_mode == 'image' and bool(bg_source)))

    watermark_source = _open_image_source(template.watermark_image) if template else None
    if watermark_source:
        _draw_image_overlay(c, watermark_source, w, h, min(bg_opacity, 0.25))

    if decorative.get('corner_decorations'):
        flourish = 1.15 * cm
        _draw_corner_flourish(c, margin + 0.6 * cm, h - margin - 0.6 * cm, flourish, 1, secondary)
        _draw_corner_flourish(c, w - margin - 0.6 * cm, h - margin - 0.6 * cm, flourish, 2, secondary)
        _draw_corner_flourish(c, margin + 0.6 * cm, margin + 0.6 * cm, flourish, 4, secondary)
        _draw_corner_flourish(c, w - margin - 0.6 * cm, margin + 0.6 * cm, flourish, 3, secondary)

    org_name = design['basic'].get('organization_name') or SITE_NAME
    logo_source = _open_image_source(template.organization_logo) if template else None
    if logo_source:
        _draw_logo(c, logo_source, w, h, margin, layout.get('logo_position', 'top-left'))

    seal_source = _open_image_source(template.seal_image) if template else None
    if seal_source and decorative.get('gold_seal'):
        _draw_image_overlay(c, seal_source, w * 0.18, h * 0.18, 1.0, centered=False)
    elif decorative.get('gold_seal'):
        _draw_award_seal(c, content_left + 0.55 * cm, h - margin - 2.15 * cm, 0.42 * cm, accent, secondary)

    if decorative.get('ribbon'):
        _draw_ribbon(c, content_center_x, h - margin - 2.5 * cm, secondary)
    if decorative.get('star_badge'):
        c.setFont('Helvetica-Bold', 14)
        c.setFillColor(secondary)
        c.drawString(content_right - 0.8 * cm, h - margin - 2.0 * cm, '★')
    if decorative.get('trophy_icon'):
        c.setFont('Helvetica-Bold', 9)
        c.setFillColor(accent)
        c.drawString(content_left + 0.2 * cm, h - margin - 2.0 * cm, 'TROPHY')
    if template and decorative.get('laurel_wreath'):
        c.setFont('Helvetica', 10)
        c.setFillColor(muted)
        c.drawCentredString(content_center_x, h - margin - 2.35 * cm, '～ ✦ ～')

    y = h - margin - 1.08 * cm
    org_header_color = colors.white if design['border'].get('style') == 'classic' else accent
    _draw_text_aligned(
        c,
        content_center_x,
        y,
        org_name.upper()[:40],
        'Helvetica-Bold',
        10,
        org_header_color,
        alignment,
        content_left,
        content_right,
    )

    y -= 1.2 * cm
    title_text = (template.title_text if template else 'Certificate of Completion')[:60]
    _draw_text_aligned(
        c,
        content_center_x,
        y,
        title_text,
        typography.get('title_font', 'Helvetica-Bold'),
        26,
        accent,
        layout.get('title_position', alignment),
        content_left,
        content_right,
    )

    y -= 0.58 * cm
    c.setStrokeColor(secondary)
    c.setLineWidth(1.6)
    line_half = min(content_width * 0.36, 5.8 * cm)
    c.line(content_center_x - line_half, y, content_center_x + line_half, y)

    y -= 0.78 * cm
    subtitle = (template.subtitle_text if template else 'This is to certify that')[:90]
    _draw_text_aligned(
        c,
        content_center_x,
        y,
        subtitle,
        typography.get('body_font', 'Helvetica'),
        int(typography.get('font_size', 11)),
        muted,
        alignment,
        content_left,
        content_right,
    )

    y -= 1.08 * cm
    name_font = typography.get('name_font') or (template.name_font if template else 'Helvetica-Bold')
    name_size = int(template.name_size if template else typography.get('name_size', 22))
    student_display = ctx.student_name[:52]
    _draw_text_aligned(
        c,
        content_center_x,
        y,
        student_display,
        name_font,
        name_size,
        name_color,
        layout.get('name_position', alignment),
        content_left,
        content_right,
    )
    underline = typography.get('name_underline', 'none')
    if underline != 'none':
        name_width = c.stringWidth(student_display, name_font, name_size)
        line_y = y - 0.12 * cm
        x_start = content_center_x - name_width / 2
        c.setStrokeColor(name_color)
        c.setLineWidth(1.2 if underline == 'solid' else 0.8)
        c.line(x_start, line_y, x_start + name_width, line_y)
        if underline == 'double':
            c.line(x_start, line_y - 0.14 * cm, x_start + name_width, line_y - 0.14 * cm)

    y -= 0.68 * cm
    meta_items = []
    if ctx.department:
        meta_items.append(f'Department · {ctx.department}')
    if ctx.roll_number:
        meta_items.append(f'Roll No · {ctx.roll_number}')
    elif ctx.username:
        meta_items.append(f'Student ID · {ctx.username}')
    if ctx.academic_year:
        meta_items.append(f'Academic Year · {ctx.academic_year}')
    if ctx.group_name:
        meta_items.append(f'Group · {ctx.group_name}')
    if meta_items:
        meta_line = '    |    '.join(meta_items)
        if c.stringWidth(meta_line, typography.get('body_font', 'Helvetica'), 9.5) > content_width:
            y = _draw_centered_lines(c, content_center_x, y, meta_items, typography.get('body_font', 'Helvetica'), 9.5, muted, 13)
        else:
            c.setFont(typography.get('body_font', 'Helvetica'), 9.5)
            c.setFillColor(muted)
            c.drawCentredString(content_center_x, y, meta_line[:120])
            y -= 0.55 * cm

    y -= 0.38 * cm
    description = design['basic'].get('description_template') or 'has successfully completed the final project submission'
    _draw_text_aligned(
        c,
        content_center_x,
        y,
        description[:100],
        typography.get('body_font', 'Helvetica'),
        int(typography.get('font_size', 11)),
        ink,
        alignment,
        content_left,
        content_right,
    )

    y -= 0.58 * cm
    title_lines = _wrap_project_title(ctx.project_title)
    y = _draw_centered_lines(c, content_center_x, y, title_lines, 'Helvetica-BoldOblique', 14, accent, 17)

    y -= 0.78 * cm
    chip_h = 1.48 * cm
    chip_gap = 0.48 * cm
    chip_count = 3
    chip_w = (content_width - chip_gap * (chip_count - 1)) / chip_count
    chip_x = content_left + (content_width - (chip_w * chip_count + chip_gap * (chip_count - 1))) / 2
    teacher_score = f'{ctx.teacher_marks}/100' if ctx.teacher_marks is not None else '—'
    final_score = f'{ctx.final_marks}/100' if ctx.final_marks is not None else '—'
    grade_display = f'{letter} · {grade_label}' if letter != '—' else 'Not graded'
    for index, (label, value) in enumerate(
        [('Grade', grade_display), ('Teacher score', teacher_score), ('Final score', final_score)]
    ):
        _draw_score_chip(c, chip_x + index * (chip_w + chip_gap), y - chip_h, chip_w, chip_h, label, value, accent, muted)

    y -= chip_h + 0.58 * cm
    c.setFont(typography.get('body_font', 'Helvetica'), 9.5)
    c.setFillColor(muted)
    c.drawCentredString(content_center_x, y, f'Completed on {completion_str}   ·   First submitted {submitted_str}')
    if ctx.teacher_name:
        y -= 0.44 * cm
        c.drawCentredString(content_center_x, y, f'Faculty guide · {ctx.teacher_name[:48]}')

    y -= 0.58 * cm
    footer = (template.footer_text if template else design['basic'].get('tagline', ''))[:120]
    _draw_text_aligned(c, content_center_x, y, footer, 'Helvetica-Bold', 9, accent, alignment, content_left, content_right)

    tagline = design['basic'].get('tagline') or f'{SITE_NAME} · Official Project Completion Record'
    c.setFont('Helvetica-BoldOblique', 8.5)
    c.setFillColor(accent)
    c.drawCentredString(content_center_x, margin + 0.38 * cm, tagline[:80])

    if qr_buf:
        qr_y = margin + 1.55 * cm
        _draw_qr_panel(c, qr_buf, qr_x, qr_y, qr_size, accent, secondary)

    signatories = design.get('signatures', {}).get('signatories') or []
    sig_source = _open_image_source(template.signature_image) if template else None
    _draw_signature_row(c, content_left, margin + 1.35 * cm, content_width, signatories, muted, sig_source)

    c.setFont('Helvetica', 8)
    c.setFillColor(muted)
    c.drawString(content_left, margin + 0.42 * cm, f'Certificate ID · {cert_id}')

    badge_source = _open_image_source(template.achievement_badge) if template else None
    if badge_source:
        _draw_image_overlay(c, badge_source, w * 0.12, h * 0.12, 1.0, centered=False)

    c.showPage()
    c.save()
    pdf = buf.getvalue()
    buf.close()
    return pdf


def build_certificate_pdf_from_report(
    report,
    *,
    verification_code: str,
    verify_url: str,
    template: CertificateTemplate | None = None,
    recipient=None,
) -> bytes:
    ctx = certificate_context_from_report(
        report,
        verification_code=verification_code,
        verify_url=verify_url,
        recipient=recipient,
    )
    return build_certificate_pdf_from_context(ctx, template=template)


# Backward compatibility for imports/tests
class CertificateTemplateStyle:
    @classmethod
    def from_template(cls, template):
        design = resolve_certificate_design(template)
        return cls(
            title_text=getattr(template, 'title_text', '') or 'Certificate of Completion',
            subtitle_text=getattr(template, 'subtitle_text', '') or 'This is to certify that',
            footer_text=getattr(template, 'footer_text', '') or '',
            accent_color=design['colors']['primary'],
            secondary_color=design['colors']['accent'],
            text_color=design['colors']['text'],
            muted_color=design['colors']['muted'],
            background_color=design['colors']['background'],
            reference_image_path=_resolve_reference_image_path(template),
            use_reference_background=getattr(template, 'use_reference_background', True),
        )

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
