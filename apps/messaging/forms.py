from django import forms

from core.presentation.form_labels import RequiredLabelsMixin
from .models import Message


class ComposeMessageForm(RequiredLabelsMixin, forms.ModelForm):
    class Meta:
        model = Message
        fields = ('receiver', 'body')
        widgets = {
            'receiver': forms.Select(attrs={'class': 'form-select rounded-3 rf-select2'}),
            'body': forms.Textarea(attrs={'class': 'form-control rounded-3', 'rows': 4, 'placeholder': 'Message…'}),
        }

    def __init__(self, *args, sender=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounts.infrastructure.models import User

        self.fields['receiver'].queryset = User.objects.filter(is_active=True).exclude(pk=sender.pk).order_by(
            'username'
        )
