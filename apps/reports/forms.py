from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from core.presentation.form_labels import RequiredLabelsMixin, apply_required_labels

from .certificate_design import (
    ALIGNMENT_CHOICES,
    BACKGROUND_MODE_CHOICES,
    BORDER_STYLE_CHOICES,
    CREATION_MODE_CHOICES,
    DEFAULT_CERTIFICATE_DESIGN,
    FONT_CHOICES,
    PAGE_SIZE_CHOICES,
    UNDERLINE_CHOICES,
    merge_certificate_design,
    normalize_hex_color,
    COLOR_FIELD_NAMES,
)
from .constants import (
    REPORT_FILE_ACCEPT,
    REPORT_FILE_INVALID_MESSAGE,
    is_allowed_report_extension,
)
from core.exceptions.base import ValidationAppError

from .models import (
    ActivityLog,
    CertificateTemplate,
    Comment,
    DeadlineExtensionRequest,
    ProjectGroup,
    ReEvaluationRequest,
    Report,
    Rubric,
    SystemSettings,
)


class ReportSubmitForm(RequiredLabelsMixin, forms.ModelForm):
    SUBMISSION_INDIVIDUAL = 'individual'
    SUBMISSION_GROUP = 'group'

    submission_type = forms.ChoiceField(
        choices=[
            (SUBMISSION_INDIVIDUAL, 'Individual project'),
            (SUBMISSION_GROUP, 'Group project'),
        ],
        initial=SUBMISSION_INDIVIDUAL,
        widget=forms.RadioSelect,
    )
    project_group_id = forms.TypedChoiceField(
        required=False,
        coerce=int,
        empty_value=None,
        choices=[],
        widget=forms.Select(attrs={'class': 'form-select rounded-3 rf-select2'}),
    )

    class Meta:
        model = Report
        fields = ('title', 'file', 'tags', 'academic_year')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control rounded-3', 'placeholder': 'Project title'}),
            'file': forms.FileInput(
                attrs={
                    'class': 'form-control app-file-input-hidden',
                    'accept': REPORT_FILE_ACCEPT,
                    'id': 'report-file-input',
                }
            ),
            'tags': forms.TextInput(
                attrs={
                    'class': 'form-control rounded-3',
                    'placeholder': 'Optional tags, comma-separated',
                }
            ),
            'academic_year': forms.TextInput(
                attrs={
                    'class': 'form-control rounded-3',
                    'placeholder': 'e.g. 2025-2026',
                    'required': 'required',
                }
            ),
        }

    def __init__(self, *args, user=None, submittable_groups=None, **kwargs):
        from apps.reports.group_helpers import teacher_display_with_department

        self.user = user
        super().__init__(*args, **kwargs)
        self.fields['academic_year'].required = True
        apply_required_labels(self)
        groups = submittable_groups or []
        self.fields['project_group_id'].choices = [('', 'Select your project group…')] + [
            (
                group.pk,
                f'{group.name} — {teacher_display_with_department(group.assigned_teacher)}',
            )
            for group in groups
        ]

    def clean_academic_year(self):
        value = (self.cleaned_data.get('academic_year') or '').strip()
        if not value:
            raise ValidationError('Academic year is required.')
        return value

    def clean(self):
        from application.services.project_group_service import ProjectGroupService

        data = super().clean()
        submission_type = data.get('submission_type', self.SUBMISSION_INDIVIDUAL)
        if submission_type == self.SUBMISSION_GROUP:
            group_id = data.get('project_group_id')
            if not group_id:
                raise ValidationError('Select a project group for a group submission.')
            try:
                group = ProjectGroupService().resolve_group_for_submit(self.user, int(group_id))
            except ValidationAppError as exc:
                raise ValidationError(str(exc)) from exc
            except Exception as exc:
                from core.exceptions.base import BusinessLogicError, NotFoundAppError, PermissionAppError

                if isinstance(exc, (ValidationAppError, BusinessLogicError, NotFoundAppError, PermissionAppError)):
                    raise ValidationError(str(exc)) from exc
                raise
            data['project_group'] = group
        else:
            data['project_group'] = None
        return data

    def clean_file(self):
        f = self.cleaned_data.get('file')
        if not f:
            return f
        if not is_allowed_report_extension(f.name):
            raise ValidationError(REPORT_FILE_INVALID_MESSAGE)
        ss = SystemSettings.get_settings()
        max_bytes = ss.max_file_size_mb * 1024 * 1024
        if f.size > max_bytes:
            raise ValidationError(
                f'File too large. Maximum size is {ss.max_file_size_mb} MB (configured in system settings).'
            )
        return f


class ReportResubmitForm(RequiredLabelsMixin, forms.Form):
    file = forms.FileField(
        widget=forms.FileInput(
            attrs={'class': 'form-control', 'accept': REPORT_FILE_ACCEPT}
        ),
    )

    def clean_file(self):
        f = self.cleaned_data.get('file')
        if not f:
            return f
        if not is_allowed_report_extension(f.name):
            raise ValidationError(REPORT_FILE_INVALID_MESSAGE)
        ss = SystemSettings.get_settings()
        max_bytes = ss.max_file_size_mb * 1024 * 1024
        if f.size > max_bytes:
            raise ValidationError(f'File too large. Maximum {ss.max_file_size_mb} MB.')
        return f


class CommentForm(RequiredLabelsMixin, forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('message',)
        widgets = {
            'message': forms.Textarea(
                attrs={'class': 'form-control rounded-3', 'rows': 3, 'placeholder': 'Write a comment...'}
            ),
        }


class ReportFilterForm(RequiredLabelsMixin, forms.Form):
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control rounded-3', 'placeholder': 'Title, username, name'}),
    )
    academic_year = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control rounded-3', 'placeholder': 'Academic year'}),
    )
    include_archived = forms.BooleanField(
        required=False,
        label='Include archived',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    status = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All statuses'),
            *Report.Status.choices,
            ('awaiting_teacher', 'Awaiting teacher review'),
            ('awaiting_admin', 'Awaiting admin (teacher OK)'),
            ('late', 'Late submissions'),
        ],
        widget=forms.Select(attrs={'class': 'form-select rounded-3 rf-select2', 'data-rf-select2-search': 'false'}),
    )
    department = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control rounded-3', 'placeholder': 'Department'}),
    )
    min_marks = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=100,
        widget=forms.NumberInput(attrs={'class': 'form-control rounded-3', 'placeholder': 'Min'}),
    )
    max_marks = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=100,
        widget=forms.NumberInput(attrs={'class': 'form-control rounded-3', 'placeholder': 'Max'}),
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control rounded-3', 'type': 'date'}),
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control rounded-3', 'type': 'date'}),
    )
    include_deleted = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )


class DeadlineForm(RequiredLabelsMixin, forms.ModelForm):
    class Meta:
        model = SystemSettings
        fields = (
            'submission_deadline',
            'max_attempts',
            'max_file_size_mb',
            'group_submission_deadline',
            'group_max_attempts',
            'group_min_members',
            'group_max_members',
        )
        widgets = {
            'submission_deadline': forms.DateTimeInput(
                attrs={'class': 'form-control rounded-3', 'type': 'datetime-local'},
            ),
            'group_submission_deadline': forms.DateTimeInput(
                attrs={'class': 'form-control rounded-3', 'type': 'datetime-local'},
            ),
            'max_attempts': forms.NumberInput(attrs={'class': 'form-control rounded-3', 'min': 1, 'max': 99}),
            'group_max_attempts': forms.NumberInput(attrs={'class': 'form-control rounded-3', 'min': 1, 'max': 99}),
            'group_min_members': forms.NumberInput(attrs={'class': 'form-control rounded-3', 'min': 2, 'max': 50}),
            'group_max_members': forms.NumberInput(attrs={'class': 'form-control rounded-3', 'min': 2, 'max': 50}),
            'max_file_size_mb': forms.NumberInput(attrs={'class': 'form-control rounded-3', 'min': 1, 'max': 100}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        datetime_fields = ('submission_deadline', 'group_submission_deadline')
        for field_name in datetime_fields:
            self.fields[field_name].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S']
            if self.instance and self.instance.pk:
                dt = getattr(self.instance, field_name, None)
                if dt:
                    if timezone.is_aware(dt):
                        dt = timezone.localtime(dt)
                    self.initial[field_name] = dt.strftime('%Y-%m-%dT%H:%M')

    def clean_submission_deadline(self):
        dt = self.cleaned_data['submission_deadline']
        if dt and timezone.is_naive(dt):
            return timezone.make_aware(dt, timezone.get_current_timezone())
        return dt

    def clean_group_submission_deadline(self):
        dt = self.cleaned_data.get('group_submission_deadline')
        if dt and timezone.is_naive(dt):
            return timezone.make_aware(dt, timezone.get_current_timezone())
        return dt

    def clean(self):
        data = super().clean()
        min_members = data.get('group_min_members')
        max_members = data.get('group_max_members')
        if min_members and max_members and min_members > max_members:
            raise ValidationError('Minimum group members cannot be greater than maximum group members.')
        return data


class CertificateTemplateForm(RequiredLabelsMixin, forms.ModelForm):
    """Full certificate designer — model fields + design_json options."""

    creation_mode = forms.ChoiceField(choices=CREATION_MODE_CHOICES, required=False)
    border_style = forms.ChoiceField(choices=BORDER_STYLE_CHOICES, required=False)
    border_width = forms.FloatField(min_value=0.5, max_value=8, required=False)
    border_radius = forms.FloatField(min_value=0, max_value=40, required=False)
    border_pattern = forms.CharField(required=False, max_length=80)
    background_mode = forms.ChoiceField(choices=BACKGROUND_MODE_CHOICES, required=False)
    background_opacity = forms.FloatField(min_value=0.1, max_value=1.0, required=False)
    title_font = forms.ChoiceField(choices=FONT_CHOICES, required=False)
    recipient_font = forms.ChoiceField(choices=FONT_CHOICES, required=False)
    body_font = forms.ChoiceField(choices=FONT_CHOICES, required=False)
    font_size = forms.IntegerField(min_value=8, max_value=24, required=False)
    font_weight = forms.ChoiceField(
        choices=[('normal', 'Normal'), ('bold', 'Bold')],
        required=False,
    )
    text_alignment = forms.ChoiceField(choices=ALIGNMENT_CHOICES, required=False)
    name_underline = forms.ChoiceField(choices=UNDERLINE_CHOICES, required=False)
    margin_cm = forms.FloatField(min_value=0.5, max_value=3.0, required=False)
    padding_cm = forms.FloatField(min_value=0.3, max_value=2.5, required=False)
    header_position = forms.ChoiceField(
        choices=[('top', 'Top'), ('center', 'Center')],
        required=False,
    )
    logo_position = forms.ChoiceField(
        choices=[('top-left', 'Top left'), ('top-center', 'Top center'), ('top-right', 'Top right')],
        required=False,
    )
    title_position = forms.ChoiceField(choices=ALIGNMENT_CHOICES, required=False)
    name_position = forms.ChoiceField(choices=ALIGNMENT_CHOICES, required=False)
    footer_position = forms.ChoiceField(
        choices=[('bottom', 'Bottom'), ('center', 'Center')],
        required=False,
    )
    decorative_gold_seal = forms.BooleanField(required=False)
    decorative_ribbon = forms.BooleanField(required=False)
    decorative_laurel = forms.BooleanField(required=False)
    decorative_trophy = forms.BooleanField(required=False)
    decorative_star = forms.BooleanField(required=False)
    decorative_corners = forms.BooleanField(required=False)
    signature_count = forms.IntegerField(min_value=1, max_value=3, required=False)
    sig1_name = forms.CharField(required=False, max_length=80)
    sig1_designation = forms.CharField(required=False, max_length=120)
    sig2_name = forms.CharField(required=False, max_length=80)
    sig2_designation = forms.CharField(required=False, max_length=120)
    sig3_name = forms.CharField(required=False, max_length=80)
    sig3_designation = forms.CharField(required=False, max_length=120)
    enable_qr = forms.BooleanField(required=False)
    certificate_id_format = forms.CharField(required=False, max_length=80)
    page_size = forms.ChoiceField(
        choices=PAGE_SIZE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select rounded-3', 'id': 'id_page_size'}),
    )
    custom_width_mm = forms.FloatField(min_value=100, max_value=600, required=False)
    custom_height_mm = forms.FloatField(min_value=100, max_value=600, required=False)

    class Meta:
        model = CertificateTemplate
        fields = (
            'name',
            'title_text',
            'subtitle_text',
            'organization_name',
            'tagline',
            'footer_text',
            'description_template',
            'organization_logo',
            'reference_image',
            'watermark_image',
            'seal_image',
            'signature_image',
            'achievement_badge',
            'accent_color',
            'secondary_color',
            'text_color',
            'muted_color',
            'background_color',
            'border_color',
            'name_color',
            'name_font',
            'name_size',
            'use_reference_background',
        )
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control rounded-3', 'placeholder': 'Template name'}),
            'title_text': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
            'subtitle_text': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
            'organization_name': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
            'tagline': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
            'footer_text': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
            'description_template': forms.TextInput(
                attrs={'class': 'form-control rounded-3', 'placeholder': 'Text shown before project title'}
            ),
            'organization_logo': forms.ClearableFileInput(
                attrs={'class': 'form-control rounded-3', 'accept': 'image/png,image/jpeg,image/webp'}
            ),
            'reference_image': forms.ClearableFileInput(
                attrs={
                    'class': 'form-control rounded-3',
                    'accept': 'image/png,image/jpeg,image/webp',
                    'id': 'id_reference_image',
                    'data-cert-reference-image': 'true',
                }
            ),
            'watermark_image': forms.ClearableFileInput(
                attrs={'class': 'form-control rounded-3', 'accept': 'image/png,image/jpeg,image/webp'}
            ),
            'seal_image': forms.ClearableFileInput(
                attrs={'class': 'form-control rounded-3', 'accept': 'image/png,image/jpeg,image/webp'}
            ),
            'signature_image': forms.ClearableFileInput(
                attrs={'class': 'form-control rounded-3', 'accept': 'image/png,image/jpeg,image/webp'}
            ),
            'achievement_badge': forms.ClearableFileInput(
                attrs={'class': 'form-control rounded-3', 'accept': 'image/png,image/jpeg,image/webp'}
            ),
            'accent_color': forms.TextInput(attrs={'class': 'form-control form-control-color rounded-3', 'type': 'color'}),
            'secondary_color': forms.TextInput(
                attrs={'class': 'form-control form-control-color rounded-3', 'type': 'color'}
            ),
            'text_color': forms.TextInput(attrs={'class': 'form-control form-control-color rounded-3', 'type': 'color'}),
            'muted_color': forms.TextInput(attrs={'class': 'form-control form-control-color rounded-3', 'type': 'color'}),
            'background_color': forms.TextInput(
                attrs={'class': 'form-control form-control-color rounded-3', 'type': 'color'}
            ),
            'border_color': forms.TextInput(
                attrs={'class': 'form-control form-control-color rounded-3', 'type': 'color'}
            ),
            'name_color': forms.TextInput(
                attrs={'class': 'form-control form-control-color rounded-3', 'type': 'color'}
            ),
            'name_font': forms.Select(attrs={'class': 'form-select rounded-3'}, choices=FONT_CHOICES),
            'name_size': forms.NumberInput(attrs={'class': 'form-control rounded-3', 'min': 14, 'max': 36}),
            'use_reference_background': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    _IMAGE_FIELDS = (
        'organization_logo',
        'reference_image',
        'watermark_image',
        'seal_image',
        'signature_image',
        'achievement_badge',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        design = merge_certificate_design(
            self.instance.design_json if self.instance and self.instance.pk else None
        )
        self._apply_design_initial(design)
        for field_name in self.fields:
            if field_name not in self._IMAGE_FIELDS and hasattr(self.fields[field_name], 'widget'):
                css = self.fields[field_name].widget.attrs.get('class', '')
                if 'form-control' not in css and 'form-select' not in css and 'form-check-input' not in css:
                    self.fields[field_name].widget.attrs['class'] = f'form-control rounded-3 {css}'.strip()

    def _apply_design_initial(self, design: dict) -> None:
        mapping = {
            'border_style': design['border']['style'],
            'border_width': design['border']['width'],
            'border_radius': design['border']['radius'],
            'border_pattern': design['border']['pattern'],
            'background_mode': design['background']['mode'],
            'background_opacity': design['background']['opacity'],
            'title_font': design['typography']['title_font'],
            'recipient_font': design['typography']['recipient_font'],
            'body_font': design['typography']['body_font'],
            'font_size': design['typography']['font_size'],
            'font_weight': design['typography']['font_weight'],
            'text_alignment': design['typography']['text_alignment'],
            'name_underline': design['typography']['name_underline'],
            'margin_cm': design['layout']['margin_cm'],
            'padding_cm': design['layout']['padding_cm'],
            'header_position': design['layout']['header_position'],
            'logo_position': design['layout']['logo_position'],
            'title_position': design['layout']['title_position'],
            'name_position': design['layout']['name_position'],
            'footer_position': design['layout']['footer_position'],
            'decorative_gold_seal': design['decorative']['gold_seal'],
            'decorative_ribbon': design['decorative']['ribbon'],
            'decorative_laurel': design['decorative']['laurel_wreath'],
            'decorative_trophy': design['decorative']['trophy_icon'],
            'decorative_star': design['decorative']['star_badge'],
            'decorative_corners': design['decorative']['corner_decorations'],
            'signature_count': design['signatures']['count'],
            'enable_qr': design['qr']['enabled'],
            'certificate_id_format': design['certificate_id']['format'],
            'page_size': design['page']['size'],
            'custom_width_mm': design['page']['custom_width_mm'],
            'custom_height_mm': design['page']['custom_height_mm'],
            'creation_mode': design.get('creation_mode', 'from_image'),
        }
        for key, value in mapping.items():
            self.fields[key].initial = value
        signatories = design['signatures']['signatories']
        for index in range(3):
            if index < len(signatories):
                self.fields[f'sig{index + 1}_name'].initial = signatories[index].get('name', '')
                self.fields[f'sig{index + 1}_designation'].initial = signatories[index].get('designation', '')

    def _build_design_json(self) -> dict:
        count = int(self.cleaned_data.get('signature_count') or 1)
        signatories = []
        positions = ['left', 'center', 'right']
        for index in range(min(count, 3)):
            signatories.append(
                {
                    'name': self.cleaned_data.get(f'sig{index + 1}_name') or f'Signatory {index + 1}',
                    'designation': self.cleaned_data.get(f'sig{index + 1}_designation') or '',
                    'position': positions[index],
                }
            )
        return {
            'border': {
                'style': self.cleaned_data.get('border_style') or DEFAULT_CERTIFICATE_DESIGN['border']['style'],
                'color': normalize_hex_color(
                    self.cleaned_data.get('border_color'),
                    DEFAULT_CERTIFICATE_DESIGN['border']['color'],
                ),
                'width': float(self.cleaned_data.get('border_width') or 2.8),
                'radius': float(self.cleaned_data.get('border_radius') or 12),
                'pattern': self.cleaned_data.get('border_pattern') or '',
            },
            'background': {
                'mode': self.cleaned_data.get('background_mode') or 'solid',
                'opacity': float(self.cleaned_data.get('background_opacity') or 1.0),
            },
            'typography': {
                'title_font': self.cleaned_data.get('title_font') or 'Helvetica-Bold',
                'recipient_font': self.cleaned_data.get('recipient_font') or 'Helvetica-Bold',
                'body_font': self.cleaned_data.get('body_font') or 'Helvetica',
                'font_size': int(self.cleaned_data.get('font_size') or 11),
                'font_weight': self.cleaned_data.get('font_weight') or 'normal',
                'text_alignment': self.cleaned_data.get('text_alignment') or 'center',
                'name_underline': self.cleaned_data.get('name_underline') or 'none',
            },
            'layout': {
                'margin_cm': float(self.cleaned_data.get('margin_cm') or 1.05),
                'padding_cm': float(self.cleaned_data.get('padding_cm') or 0.9),
                'header_position': self.cleaned_data.get('header_position') or 'top',
                'logo_position': self.cleaned_data.get('logo_position') or 'top-left',
                'title_position': self.cleaned_data.get('title_position') or 'center',
                'name_position': self.cleaned_data.get('name_position') or 'center',
                'footer_position': self.cleaned_data.get('footer_position') or 'bottom',
            },
            'decorative': {
                'gold_seal': bool(self.cleaned_data.get('decorative_gold_seal')),
                'ribbon': bool(self.cleaned_data.get('decorative_ribbon')),
                'laurel_wreath': bool(self.cleaned_data.get('decorative_laurel')),
                'trophy_icon': bool(self.cleaned_data.get('decorative_trophy')),
                'star_badge': bool(self.cleaned_data.get('decorative_star')),
                'corner_decorations': bool(self.cleaned_data.get('decorative_corners')),
            },
            'signatures': {'count': count, 'signatories': signatories},
            'qr': {'enabled': bool(self.cleaned_data.get('enable_qr', True))},
            'certificate_id': {
                'format': self.cleaned_data.get('certificate_id_format') or 'RF-{code}',
            },
            'page': {
                'size': self.cleaned_data.get('page_size') or 'a4_landscape',
                'custom_width_mm': float(self.cleaned_data.get('custom_width_mm') or 297),
                'custom_height_mm': float(self.cleaned_data.get('custom_height_mm') or 210),
            },
            'creation_mode': self.cleaned_data.get('creation_mode') or 'from_image',
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('page_size') == 'custom':
            if not cleaned.get('custom_width_mm') or not cleaned.get('custom_height_mm'):
                raise ValidationError('Custom page size requires width and height in millimeters.')
        defaults = {
            'accent_color': DEFAULT_CERTIFICATE_DESIGN['colors']['primary'],
            'secondary_color': DEFAULT_CERTIFICATE_DESIGN['colors']['accent'],
            'text_color': DEFAULT_CERTIFICATE_DESIGN['colors']['text'],
            'muted_color': DEFAULT_CERTIFICATE_DESIGN['colors']['muted'],
            'background_color': DEFAULT_CERTIFICATE_DESIGN['colors']['background'],
            'border_color': DEFAULT_CERTIFICATE_DESIGN['border']['color'],
            'name_color': DEFAULT_CERTIFICATE_DESIGN['colors']['name'],
        }
        for field_name in COLOR_FIELD_NAMES:
            cleaned[field_name] = normalize_hex_color(
                cleaned.get(field_name),
                defaults.get(field_name, '#2d5a47'),
            )
        return cleaned

    def clean_reference_image(self):
        return self._clean_image('reference_image')

    def clean_organization_logo(self):
        return self._clean_image('organization_logo')

    def clean_watermark_image(self):
        return self._clean_image('watermark_image')

    def clean_seal_image(self):
        return self._clean_image('seal_image')

    def clean_signature_image(self):
        return self._clean_image('signature_image')

    def clean_achievement_badge(self):
        return self._clean_image('achievement_badge')

    def _clean_image(self, field_name: str):
        uploaded = self.cleaned_data.get(field_name)
        if uploaded and hasattr(uploaded, 'size') and uploaded.size > 5 * 1024 * 1024:
            raise ValidationError(f'{field_name.replace("_", " ").title()} must be 5 MB or smaller.')
        return uploaded

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.design_json = self._build_design_json()
        if commit:
            instance.save()
        return instance


class TeacherEvaluationForm(RequiredLabelsMixin, forms.Form):
    teacher_marks = forms.IntegerField(
        min_value=0,
        max_value=100,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control rounded-3'}),
    )
    feedback = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control rounded-3', 'rows': 3, 'placeholder': 'Feedback for student'}),
    )
    is_final_submission = forms.BooleanField(
        required=False,
        initial=False,
        label='This is the final submission — student receives a completion certificate after admin approval',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )


class AdminFinalMarksForm(RequiredLabelsMixin, forms.Form):
    marks = forms.IntegerField(
        min_value=0,
        max_value=100,
        required=True,
        widget=forms.NumberInput(attrs={'class': 'form-control rounded-3'}),
    )


class ReEvaluationRequestForm(RequiredLabelsMixin, forms.ModelForm):
    class Meta:
        model = ReEvaluationRequest
        fields = ('reason',)
        widgets = {
            'reason': forms.Textarea(
                attrs={'class': 'form-control rounded-3', 'rows': 3, 'placeholder': 'Why should marks be reviewed?'}
            ),
        }


class BulkReportIdsForm(RequiredLabelsMixin, forms.Form):
    report_ids = forms.CharField(widget=forms.HiddenInput())
    action = forms.ChoiceField(
        choices=[('approve', 'Approve'), ('reject', 'Reject')],
        widget=forms.HiddenInput(),
    )


class ActivityLogFilterForm(RequiredLabelsMixin, forms.Form):
    user_search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control rounded-3', 'placeholder': 'Username'}),
    )
    action = forms.ChoiceField(
        required=False,
        choices=[('', 'All actions')] + list(ActivityLog.Action.choices),
        widget=forms.Select(attrs={'class': 'form-select rounded-3 rf-select2', 'data-rf-select2-search': 'false'}),
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control rounded-3', 'type': 'date'}),
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control rounded-3', 'type': 'date'}),
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control rounded-3', 'placeholder': 'Detail text'}),
    )


class DeadlineExtensionRequestForm(RequiredLabelsMixin, forms.ModelForm):
    class Meta:
        model = DeadlineExtensionRequest
        fields = ('reason',)
        widgets = {
            'reason': forms.Textarea(
                attrs={'class': 'form-control rounded-3', 'rows': 3, 'placeholder': 'Why do you need more time?'}
            ),
        }


class ProjectGroupCreateForm(RequiredLabelsMixin, forms.Form):
    name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control rounded-3', 'placeholder': 'Group / project name'}),
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={'class': 'form-control rounded-3', 'rows': 3, 'placeholder': 'Optional short description'}
        ),
    )
    project_mate_ids = forms.CharField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        apply_required_labels(self)

    def clean(self):
        from apps.reports.group_helpers import parse_mate_ids, validate_project_mates

        data = super().clean()
        mate_ids = parse_mate_ids(data.get('project_mate_ids'))
        try:
            validate_project_mates(self.user, mate_ids)
        except ValidationAppError as exc:
            raise ValidationError(str(exc)) from exc
        data['project_mate_ids_list'] = mate_ids
        return data


class ProjectGroupAssignTeacherForm(RequiredLabelsMixin, forms.Form):
    teacher_id = forms.TypedChoiceField(
        required=False,
        coerce=lambda value: int(value) if value else None,
        empty_value=None,
        choices=[],
        widget=forms.Select(attrs={'class': 'form-select rounded-3 rf-select2', 'data-rf-select2-search': 'true'}),
    )

    def __init__(self, *args, group=None, **kwargs):
        self.group = group
        super().__init__(*args, **kwargs)
        from apps.reports.group_helpers import get_teachers_for_department

        teachers = get_teachers_for_department(getattr(group, 'department', '') if group else '')
        self.fields['teacher_id'].choices = [('', 'No teacher assigned')] + [
            (teacher.pk, teacher.get_full_name() or teacher.username) for teacher in teachers
        ]
        if group and group.assigned_teacher_id:
            self.initial['teacher_id'] = group.assigned_teacher_id
