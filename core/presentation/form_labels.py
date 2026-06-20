"""Required-field asterisk labels for Django forms."""

from django.utils.html import escape
from django.utils.safestring import mark_safe

REQUIRED_MARK = mark_safe(' <span class="rf-required-mark text-danger" aria-hidden="true">*</span>')


def mark_required_label(label):
    if label is False or label is None:
        return label
    text = str(label)
    if 'rf-required-mark' in text:
        return mark_safe(text) if '<' in text else text
    return mark_safe(f'{escape(text)}{REQUIRED_MARK}')


def apply_required_labels(form):
    """Append * to labels for required fields; strip mark from optional fields."""
    for name, field in form.fields.items():
        if field.required:
            if field.label is not False:
                fallback = name.replace('_', ' ').title()
                field.label = mark_required_label(field.label or fallback)
            field.widget.attrs.setdefault('aria-required', 'true')
            field.widget.attrs.setdefault('data-rf-required', 'true')
        elif field.label and 'rf-required-mark' in str(field.label):
            from django.utils.html import strip_tags

            field.label = strip_tags(str(field.label)).replace('*', '').strip()


class RequiredLabelsMixin:
    """Apply required-field asterisks after the form fields are configured."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_required_labels(self)
