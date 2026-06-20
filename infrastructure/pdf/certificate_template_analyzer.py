"""Extract design hints from an admin-uploaded certificate reference image."""
from __future__ import annotations

from collections import Counter
from typing import Any

MIN_IMAGE_WIDTH = 480
MIN_IMAGE_HEIGHT = 340
MIN_BLUR_SCORE = 12.0


class CertificateImageAnalysisError(Exception):
    """User-friendly analysis failure."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def _rgb_to_hex(red: int, green: int, blue: int) -> str:
    return f'#{red:02x}{green:02x}{blue:02x}'


def _luminance(red: int, green: int, blue: int) -> float:
    return (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255.0


def _saturation(red: int, green: int, blue: int) -> float:
    values = (red, green, blue)
    max_val = max(values)
    min_val = min(values)
    if max_val == 0:
        return 0.0
    return (max_val - min_val) / max_val


def _quantize_channel(value: int) -> int:
    return int(round(value / 24.0)) * 24


def _bucket_key(red: int, green: int, blue: int) -> tuple[int, int, int]:
    return (_quantize_channel(red), _quantize_channel(green), _quantize_channel(blue))


def _estimate_blur_score(image) -> float:
    from PIL import ImageFilter, ImageStat

    gray = image.convert('L')
    edges = gray.filter(ImageFilter.FIND_EDGES)
    return float(ImageStat.Stat(edges).rms[0])


def _detect_page_size(width: int, height: int) -> str:
    ratio = width / max(height, 1)
    if ratio >= 1.2:
        return 'a4_landscape'
    if ratio <= 0.85:
        return 'a4_portrait'
    return 'a4_landscape'


def _detect_border_style(accent_sat: float, secondary_sat: float) -> str:
    if accent_sat >= 0.35 and secondary_sat >= 0.3:
        return 'royal'
    if accent_sat >= 0.22:
        return 'classic'
    if accent_sat < 0.12:
        return 'minimal'
    return 'modern'


def _detect_signature_count(image) -> int:
    """Estimate signatory lines from dark pixels in bottom band."""
    from PIL import ImageOps

    width, height = image.size
    band = image.crop((0, int(height * 0.72), width, height)).convert('L')
    band = ImageOps.autocontrast(band)
    pixels = band.load()
    row_scores: list[tuple[int, int]] = []
    for y in range(band.size[1]):
        dark = sum(1 for x in range(band.size[0]) if pixels[x, y] < 95)
        if dark > band.size[0] * 0.08:
            row_scores.append((y, dark))
    if not row_scores:
        return 2
    row_scores.sort(key=lambda item: item[1], reverse=True)
    strong_rows = [row for row in row_scores if row[1] > band.size[0] * 0.12][:3]
    return max(min(len(strong_rows) or 2, 3), 1)


def _validate_image(image) -> None:
    width, height = image.size
    if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
        raise CertificateImageAnalysisError(
            f'Image is too small ({width}×{height}px). Upload a clear certificate at least '
            f'{MIN_IMAGE_WIDTH}×{MIN_IMAGE_HEIGHT}px.'
        )
    blur_score = _estimate_blur_score(image)
    if blur_score < MIN_BLUR_SCORE:
        raise CertificateImageAnalysisError(
            'This image looks blurry or low quality. Upload a sharper, well-lit certificate scan or PNG.'
        )


def analyze_reference_image(image_source) -> dict[str, Any]:
    """
    Derive certificate design hints from a reference image.
    Returns colors plus editable design suggestions for the admin form.
    """
    from PIL import Image

    try:
        image = Image.open(image_source).convert('RGB')
    except Exception as exc:
        raise CertificateImageAnalysisError(
            'Could not read that file. Upload a PNG, JPG, or WEBP certificate image.'
        ) from exc

    _validate_image(image)
    full_width, full_height = image.size
    analysis_image = image.copy()
    analysis_image.thumbnail((420, 420))
    width, height = analysis_image.size

    pixels = list(analysis_image.getdata())
    if not pixels:
        raise CertificateImageAnalysisError('The uploaded image appears empty. Try another file.')

    counter: Counter[tuple[int, int, int]] = Counter(_bucket_key(*px) for px in pixels)
    ranked = counter.most_common()

    background = ranked[0][0]
    accent = background
    secondary = background

    for rgb, _count in ranked[1:12]:
        if _saturation(*rgb) >= 0.18 and 0.12 < _luminance(*rgb) < 0.82:
            accent = rgb
            break

    for rgb, _count in ranked[1:20]:
        if rgb == accent:
            continue
        if _saturation(*rgb) >= 0.25 and _luminance(*rgb) > 0.35:
            secondary = rgb
            break

    bg_lum = _luminance(*background)
    text = (18, 18, 18) if bg_lum > 0.58 else (247, 243, 235)
    muted = (92, 92, 92) if bg_lum > 0.58 else (200, 196, 188)
    accent_hex = _rgb_to_hex(*accent)
    secondary_hex = _rgb_to_hex(*secondary)
    border_style = _detect_border_style(_saturation(*accent), _saturation(*secondary))
    signature_count = _detect_signature_count(analysis_image)
    page_size = _detect_page_size(full_width, full_height)
    blur_score = _estimate_blur_score(analysis_image)

    signatories = [
        {'name': 'Faculty Guide', 'designation': 'Faculty Guide', 'position': 'left'},
        {'name': 'Head of Department', 'designation': 'Head of Department', 'position': 'center'},
        {'name': 'Principal', 'designation': 'Principal', 'position': 'right'},
    ][:signature_count]

    design = {
        'border': {
            'style': border_style,
            'color': accent_hex,
            'width': 2.8 if border_style != 'minimal' else 1.2,
            'radius': 12 if border_style != 'minimal' else 6,
            'pattern': '',
        },
        'background': {
            'mode': 'image',
            'opacity': 1.0,
        },
        'typography': {
            'title_font': 'Helvetica-Bold',
            'recipient_font': 'Helvetica-Bold',
            'body_font': 'Helvetica',
            'font_size': 11,
            'font_weight': 'normal',
            'text_alignment': 'center',
            'name_font': 'Helvetica-Bold',
            'name_size': 22,
            'name_underline': 'none',
        },
        'layout': {
            'margin_cm': 1.05,
            'padding_cm': 0.9,
            'header_position': 'top',
            'logo_position': 'top-left',
            'title_position': 'center',
            'name_position': 'center',
            'footer_position': 'bottom',
        },
        'decorative': {
            'gold_seal': border_style in ('classic', 'royal'),
            'ribbon': border_style == 'royal',
            'laurel_wreath': False,
            'trophy_icon': False,
            'star_badge': border_style == 'royal',
            'corner_decorations': border_style in ('classic', 'royal'),
        },
        'signatures': {
            'count': signature_count,
            'signatories': signatories,
        },
        'page': {
            'size': page_size,
            'custom_width_mm': round(full_width * 0.264583, 1),
            'custom_height_mm': round(full_height * 0.264583, 1),
        },
        'creation_mode': 'from_image',
    }

    return {
        'accent_color': accent_hex,
        'secondary_color': secondary_hex,
        'background_color': _rgb_to_hex(*background),
        'text_color': _rgb_to_hex(*text),
        'muted_color': _rgb_to_hex(*muted),
        'border_color': accent_hex,
        'name_color': accent_hex,
        'use_reference_background': True,
        'design': design,
        'style_json': {
            'source': 'reference_image',
            'background_luminance': round(bg_lum, 3),
            'sample_size': len(pixels),
            'blur_score': round(blur_score, 2),
            'detected_signatures': signature_count,
            'detected_page_size': page_size,
        },
    }
