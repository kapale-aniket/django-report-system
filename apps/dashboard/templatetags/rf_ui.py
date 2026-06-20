from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

from core.presentation.form_labels import REQUIRED_MARK, mark_required_label

register = template.Library()


@register.simple_tag
def rf_required_mark():
    return REQUIRED_MARK


@register.simple_tag
def rf_label(label, required=False):
    if required:
        return mark_required_label(label)
    return mark_safe(escape(label))


@register.filter
def rf_field_label(field):
    if getattr(field.field, 'required', False):
        return mark_required_label(field.label or field.name.replace('_', ' ').title())
    return field.label


@register.inclusion_tag('partials/form_errors_toast.html')
def form_errors_toast(form):
    items = []
    if form is not None and form.errors:
        for error in form.non_field_errors():
            items.append({'text': str(error), 'type': 'error'})
        for field in form:
            for error in field.errors:
                label = field.label or field.name
                items.append({'text': f'{label}: {error}', 'type': 'error'})
    return {'items': items}
