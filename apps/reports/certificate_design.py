"""Certificate template design defaults and merge helpers."""
from __future__ import annotations

import copy
from typing import Any

DEFAULT_CERTIFICATE_DESIGN: dict[str, Any] = {
    'basic': {
        'organization_name': 'ReportFlow',
        'tagline': 'Official Project Completion Record',
        'description_template': 'has successfully completed the final project submission',
    },
    'border': {
        'style': 'classic',
        'color': '#2d5a47',
        'width': 2.8,
        'radius': 12,
        'pattern': '',
    },
    'colors': {
        'primary': '#2d5a47',
        'accent': '#c9a227',
        'background': '#faf6ee',
        'text': '#2c2c2c',
        'muted': '#5c5c5c',
        'name': '#2d5a47',
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
    'background': {
        'mode': 'solid',
        'opacity': 1.0,
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
        'gold_seal': True,
        'ribbon': False,
        'laurel_wreath': False,
        'trophy_icon': False,
        'star_badge': False,
        'corner_decorations': True,
    },
    'signatures': {
        'count': 3,
        'signatories': [
            {'name': 'Faculty Guide', 'designation': 'Faculty Guide', 'position': 'left'},
            {'name': 'Head of Department', 'designation': 'Head of Department', 'position': 'center'},
            {'name': 'Principal', 'designation': 'Principal', 'position': 'right'},
        ],
    },
    'qr': {
        'enabled': True,
    },
    'certificate_id': {
        'format': 'RF-{code}',
    },
    'page': {
        'size': 'a4_landscape',
        'custom_width_mm': 297,
        'custom_height_mm': 210,
    },
    'creation_mode': 'from_image',
}

CREATION_MODE_CHOICES = [
    ('from_image', 'Generate from reference image'),
    ('from_scratch', 'Build from scratch'),
]

BORDER_STYLE_CHOICES = [
    ('classic', 'Classic'),
    ('modern', 'Modern'),
    ('royal', 'Royal'),
    ('minimal', 'Minimal'),
]

BACKGROUND_MODE_CHOICES = [
    ('solid', 'Solid color'),
    ('gradient', 'Gradient'),
    ('texture', 'Texture'),
    ('image', 'Background image'),
]

PAGE_SIZE_CHOICES = [
    ('a4_landscape', 'A4 Landscape'),
    ('a4_portrait', 'A4 Portrait'),
    ('letter', 'Letter size'),
    ('custom', 'Custom width/height'),
]

FONT_CHOICES = [
    ('Helvetica', 'Helvetica'),
    ('Helvetica-Bold', 'Helvetica Bold'),
    ('Times-Roman', 'Times Roman'),
    ('Times-Bold', 'Times Bold'),
    ('Courier', 'Courier'),
]

ALIGNMENT_CHOICES = [
    ('left', 'Left'),
    ('center', 'Center'),
    ('right', 'Right'),
]

UNDERLINE_CHOICES = [
    ('none', 'None'),
    ('solid', 'Solid'),
    ('double', 'Double'),
]

COLOR_FIELD_NAMES = (
    'accent_color',
    'secondary_color',
    'text_color',
    'muted_color',
    'background_color',
    'border_color',
    'name_color',
)


def normalize_hex_color(value: str | None, fallback: str = '#2d5a47') -> str:
    """Normalize browser/API color values to #rrggbb for CharField(max_length=7)."""
    if not value:
        return fallback
    raw = str(value).strip().lower()
    if raw.startswith('#'):
        hex_digits = ''.join(ch for ch in raw[1:] if ch in '0123456789abcdef')
        if len(hex_digits) >= 6:
            return f'#{hex_digits[:6]}'
    elif len(raw) >= 6 and all(ch in '0123456789abcdef' for ch in raw[:6]):
        return f'#{raw[:6]}'
    return fallback


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def merge_certificate_design(design_json: dict[str, Any] | None) -> dict[str, Any]:
    return _deep_merge(DEFAULT_CERTIFICATE_DESIGN, design_json or {})


def resolve_certificate_design(template) -> dict[str, Any]:
    """Merge stored JSON with model field values (model fields win for text/colors)."""
    design = merge_certificate_design(getattr(template, 'design_json', None) or {})

    if template is None:
        return design

    design['basic']['organization_name'] = (
        getattr(template, 'organization_name', '') or design['basic']['organization_name']
    )
    design['basic']['tagline'] = getattr(template, 'tagline', '') or design['basic']['tagline']
    design['basic']['description_template'] = (
        getattr(template, 'description_template', '') or design['basic']['description_template']
    )

    design['colors']['primary'] = template.accent_color or design['colors']['primary']
    design['colors']['accent'] = template.secondary_color or design['colors']['accent']
    design['colors']['background'] = template.background_color or design['colors']['background']
    design['colors']['text'] = template.text_color or design['colors']['text']
    design['colors']['muted'] = template.muted_color or design['colors']['muted']
    design['colors']['name'] = getattr(template, 'name_color', '') or design['colors']['name']

    design['border']['color'] = getattr(template, 'border_color', '') or design['border']['color']
    design['typography']['name_font'] = getattr(template, 'name_font', '') or design['typography']['name_font']
    design['typography']['name_size'] = getattr(template, 'name_size', None) or design['typography']['name_size']

    return design


def format_certificate_id(code: str, design: dict[str, Any], *, year: str | None = None) -> str:
    pattern = design.get('certificate_id', {}).get('format') or 'RF-{code}'
    from django.utils import timezone

    now = timezone.localtime(timezone.now())
    return (
        pattern.replace('{code}', code)
        .replace('{year}', year or str(now.year))
        .replace('{month}', f'{now.month:02d}')
    )[:48]
