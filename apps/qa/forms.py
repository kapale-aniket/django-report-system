from django import forms

from core.presentation.form_labels import RequiredLabelsMixin, apply_required_labels
from .models import UserQuestion, VisitorQuestion


class AskQuestionForm(RequiredLabelsMixin, forms.ModelForm):
    class Meta:
        model = UserQuestion
        fields = ('subject', 'body')
        widgets = {
            'subject': forms.TextInput(
                attrs={
                    'class': 'form-control rounded-3',
                    'placeholder': 'Short topic (optional)',
                }
            ),
            'body': forms.Textarea(
                attrs={
                    'class': 'form-control rounded-3',
                    'rows': 4,
                    'placeholder': 'Describe your question about the system…',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['subject'].required = False
        self.fields['body'].required = True
        apply_required_labels(self)


class VisitorQuestionForm(RequiredLabelsMixin, forms.ModelForm):
    class Meta:
        model = VisitorQuestion
        fields = ('name', 'email', 'subject', 'body')
        widgets = {
            'name': forms.TextInput(
                attrs={
                    'class': 'form-control rounded-3',
                    'placeholder': 'Your name (optional)',
                    'autocomplete': 'name',
                }
            ),
            'email': forms.EmailInput(
                attrs={
                    'class': 'form-control rounded-3',
                    'placeholder': 'you@example.com',
                    'autocomplete': 'email',
                }
            ),
            'subject': forms.TextInput(
                attrs={
                    'class': 'form-control rounded-3',
                    'placeholder': 'Topic — e.g. login, submission flow',
                }
            ),
            'body': forms.Textarea(
                attrs={
                    'class': 'form-control rounded-3',
                    'rows': 4,
                    'placeholder': 'Ask about project workflow, approvals, or sign-in issues…',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('email', 'subject', 'body'):
            self.fields[name].required = True
        apply_required_labels(self)


class ReplyForm(RequiredLabelsMixin, forms.Form):
    answer_text = forms.CharField(
        label='Reply',
        widget=forms.Textarea(
            attrs={
                'class': 'form-control rounded-3',
                'rows': 4,
                'placeholder': 'Type the official answer for the user…',
            }
        ),
    )
