from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.decorators import role_required
from apps.accounts.infrastructure.models import User

from .forms import AskQuestionForm, ReplyForm
from .models import FAQ, UserQuestion, VisitorQuestion
from .utils import send_visitor_answer_email


@login_required
def qa_home(request):
    """FAQ accordion + ask form + my questions; admin sees pending queue."""
    faqs = FAQ.objects.filter(is_active=True)
    my_questions = UserQuestion.objects.filter(user=request.user)[:50]

    pending_for_admin = []
    pending_visitors = []
    if request.user.role == User.Role.ADMIN:
        pending_for_admin = UserQuestion.objects.filter(status=UserQuestion.Status.OPEN).select_related('user')[:100]
        pending_visitors = VisitorQuestion.objects.filter(status=VisitorQuestion.Status.OPEN)[:100]

    if request.method == 'POST' and 'ask_submit' in request.POST:
        form = AskQuestionForm(request.POST)
        if form.is_valid():
            user_question = form.save(commit=False)
            user_question.user = request.user
            user_question.save()
            messages.success(request, 'Your question was submitted. An administrator will reply soon.')
            return redirect('qa:home')
    else:
        form = AskQuestionForm()

    return render(
        request,
        'qa/home.html',
        {
            'faqs': faqs,
            'form': form,
            'my_questions': my_questions,
            'pending_for_admin': pending_for_admin,
            'pending_visitors': pending_visitors,
        },
    )


@login_required
@role_required(User.Role.ADMIN)
def qa_reply(request, pk):
    if request.method != 'POST':
        return redirect('qa:home')
    user_question = get_object_or_404(UserQuestion, pk=pk)
    if user_question.status != UserQuestion.Status.OPEN:
        messages.warning(request, 'This question is already answered.')
        return redirect('qa:home')
    form = ReplyForm(request.POST)
    if form.is_valid():
        user_question.answer_text = form.cleaned_data['answer_text'].strip()
        user_question.status = UserQuestion.Status.ANSWERED
        user_question.answered_by = request.user
        user_question.answered_at = timezone.now()
        user_question.save()
        messages.success(request, 'Reply saved.')
    else:
        messages.error(request, 'Please enter a reply.')
    return redirect('qa:home')


@login_required
@role_required(User.Role.ADMIN)
def visitor_reply(request, pk):
    if request.method != 'POST':
        return redirect('qa:home')
    visitor_question = get_object_or_404(VisitorQuestion, pk=pk)
    if visitor_question.status != VisitorQuestion.Status.OPEN:
        messages.warning(request, 'This inquiry is already answered.')
        return redirect('qa:home')
    form = ReplyForm(request.POST)
    if form.is_valid():
        visitor_question.answer_text = form.cleaned_data['answer_text'].strip()
        visitor_question.status = VisitorQuestion.Status.ANSWERED
        visitor_question.answered_by = request.user
        visitor_question.answered_at = timezone.now()
        visitor_question.save()
        send_visitor_answer_email(visitor_question)
        messages.success(request, 'Reply saved and emailed to the visitor (if mail is configured).')
    else:
        messages.error(request, 'Please enter a reply.')
    return redirect('qa:home')
