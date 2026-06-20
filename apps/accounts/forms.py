from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)
from django.core.exceptions import ValidationError

from core.presentation.form_labels import RequiredLabelsMixin, apply_required_labels
from .department_choices import ADD_DEPARTMENT_VALUE, get_department_choices
from .teacher_select import ADD_TEACHER_VALUE
from .models import User

SELECT2_CLASS = 'form-select rounded-3 rf-select2'
SELECT2_CLASS_LG = 'form-select form-select-lg rf-select2'
SELECT2_SEARCH = {'data-placeholder': 'Search…', 'data-rf-select2-clear': 'true'}


class BootstrapPasswordResetForm(RequiredLabelsMixin, PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update(
            {
                'class': 'form-control form-control-lg',
                'placeholder': ' ',
                'autocomplete': 'email',
                'autofocus': True,
            }
        )


class BootstrapSetPasswordForm(RequiredLabelsMixin, SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].widget.attrs.update(
            {
                'class': 'form-control form-control-lg',
                'placeholder': ' ',
                'autocomplete': 'new-password',
            }
        )
        self.fields['new_password2'].widget.attrs.update(
            {
                'class': 'form-control form-control-lg',
                'placeholder': ' ',
                'autocomplete': 'new-password',
            }
        )


class RoleLoginForm(RequiredLabelsMixin, AuthenticationForm):
    """Username/password login for all roles."""

    error_messages = {
        **AuthenticationForm.error_messages,
        'inactive': (
            'Your account is pending approval. Students: wait for an administrator or your assigned teacher. '
            'Teachers: wait for an administrator to activate your account.'
        ),
    }

    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-lg',
                'autofocus': True,
                'placeholder': ' ',
                'autocomplete': 'username',
            }
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={'class': 'form-control form-control-lg', 'placeholder': ' ', 'autocomplete': 'current-password'}
        )
    )

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        if username is not None and password:
            user = User.objects.filter(username=username).first()
            if user and user.check_password(password) and not user.is_active:
                raise ValidationError(
                    self.error_messages['inactive'],
                    code='inactive',
                )
        return super().clean()


class StudentRegistrationForm(RequiredLabelsMixin, UserCreationForm):
    """Self-registration — account inactive until admin or assigned teacher approves."""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'you@college.edu'}),
    )
    first_name = forms.CharField(
        max_length=150, widget=forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': ' '})
    )
    last_name = forms.CharField(
        max_length=150, widget=forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': ' '})
    )
    department = forms.ChoiceField(
        required=False,
        choices=[],
        widget=forms.Select(attrs={'class': SELECT2_CLASS_LG, **SELECT2_SEARCH}),
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'department', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': ' '}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        extra_dept = []
        if self.is_bound:
            posted = (self.data.get('department') or '').strip()
            if posted:
                extra_dept.append(posted)
        self.fields['department'].choices = get_department_choices(extra=extra_dept)
        for name in ('email', 'first_name', 'last_name', 'password1', 'password2'):
            self.fields[name].widget.attrs.setdefault('class', 'form-control form-control-lg')
            self.fields[name].widget.attrs.setdefault('placeholder', ' ')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.STUDENT
        user.is_active = False
        if commit:
            user.save()
        return user


class TeacherRegistrationForm(RequiredLabelsMixin, UserCreationForm):
    """Self-registration — inactive until an administrator approves."""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'you@college.edu'}),
    )
    first_name = forms.CharField(
        max_length=150, widget=forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': ' '})
    )
    last_name = forms.CharField(
        max_length=150, widget=forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': ' '})
    )
    department = forms.ChoiceField(
        required=False,
        choices=[],
        widget=forms.Select(attrs={'class': SELECT2_CLASS_LG, **SELECT2_SEARCH}),
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'department', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': ' '}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        extra_dept = []
        if self.is_bound:
            posted = (self.data.get('department') or '').strip()
            if posted:
                extra_dept.append(posted)
        self.fields['department'].choices = get_department_choices(extra=extra_dept)
        for name in ('email', 'first_name', 'last_name', 'password1', 'password2'):
            self.fields[name].widget.attrs.setdefault('class', 'form-control form-control-lg')
            self.fields[name].widget.attrs.setdefault('placeholder', ' ')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.TEACHER
        user.is_active = False
        if commit:
            user.save()
        return user


class AdminCreateUserForm(RequiredLabelsMixin, forms.ModelForm):
    """Admin creates student/teacher; password is auto-generated in the view."""

    department = forms.ChoiceField(
        required=False,
        choices=[],
        widget=forms.Select(attrs={'class': SELECT2_CLASS, **SELECT2_SEARCH}),
    )
    assigned_teacher = forms.ChoiceField(
        required=False,
        choices=[('', 'Select department first…')],
        widget=forms.Select(
            attrs={
                'class': SELECT2_CLASS,
                'data-placeholder': 'Search teachers…',
                'data-rf-select2-clear': 'true',
            }
        ),
    )

    class Meta:
        model = User
        fields = (
            'first_name',
            'last_name',
            'email',
            'role',
            'department',
        )
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
            'email': forms.EmailInput(attrs={'class': 'form-control rounded-3'}),
            'role': forms.Select(attrs={'class': SELECT2_CLASS, **SELECT2_SEARCH}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        extra_dept = []
        if self.instance and self.instance.pk and self.instance.department:
            extra_dept = [self.instance.department]
        if self.is_bound:
            posted = (self.data.get('department') or '').strip()
            if posted:
                extra_dept.append(posted)
        self.fields['department'].choices = get_department_choices(extra=extra_dept, include_add_option=True)
        self.fields['department'].widget.attrs.update(
            {
                'id': 'userCreateDepartment',
                'data-rf-department-select': 'true',
            }
        )
        self.fields['role'].choices = [
            c for c in User.Role.choices if c[0] != User.Role.ADMIN
        ]
        self.fields['role'].widget.attrs.update({'id': 'userCreateRole'})
        self.fields['assigned_teacher'].widget.attrs.update(
            {
                'id': 'userCreateAssignedTeacher',
                'data-rf-teacher-select': 'true',
            }
        )
        self.fields['assigned_teacher'].required = False
        self.fields['department'].required = False
        self.fields['email'].required = True
        apply_required_labels(self)

    def clean_department(self):
        department = (self.cleaned_data.get('department') or '').strip()
        if department == ADD_DEPARTMENT_VALUE:
            raise ValidationError('Select a department or use “Add department…” to create one first.')
        return department

    def clean_assigned_teacher(self):
        teacher_value = (self.cleaned_data.get('assigned_teacher') or '').strip()
        if not teacher_value:
            return None
        if teacher_value == ADD_TEACHER_VALUE:
            raise ValidationError('Select a teacher or use “Add teacher…” to create one first.')
        try:
            teacher_id = int(teacher_value)
        except (TypeError, ValueError) as exc:
            raise ValidationError('Invalid teacher selected.') from exc
        teacher = User.objects.filter(pk=teacher_id, role=User.Role.TEACHER).first()
        if teacher is None:
            raise ValidationError('Invalid teacher selected.')
        return teacher

    def clean(self):
        data = super().clean()
        if data.get('role') != User.Role.STUDENT:
            data['assigned_teacher'] = None
        return data

    def clean_email(self):
        from infrastructure.email.messages import normalize_email

        return normalize_email(self.cleaned_data.get('email', ''))


class AssignTeacherForm(RequiredLabelsMixin, forms.Form):
    student_id = forms.IntegerField(widget=forms.HiddenInput())
    assigned_teacher = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': SELECT2_CLASS, **SELECT2_SEARCH}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_teacher'].queryset = User.objects.filter(role=User.Role.TEACHER).order_by(
            'username'
        )


class UserFilterForm(RequiredLabelsMixin, forms.Form):
    status = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All statuses'),
            ('pending', 'Pending approval'),
            ('active', 'Active'),
        ],
        widget=forms.Select(attrs={'class': SELECT2_CLASS, **SELECT2_SEARCH}),
    )
    role = forms.ChoiceField(
        required=False,
        choices=[('', 'All roles')] + list(User.Role.choices),
        widget=forms.Select(attrs={'class': SELECT2_CLASS, **SELECT2_SEARCH}),
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control rounded-3', 'placeholder': 'Name or username'}),
    )
