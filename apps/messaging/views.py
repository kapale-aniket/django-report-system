from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.infrastructure.models import User

from .forms import ComposeMessageForm
from .models import Message

@login_required
def inbox(request):
    box = request.GET.get('box', 'inbox')
    if box == 'sent':
        qs = Message.objects.filter(sender=request.user).select_related('receiver')
    else:
        qs = Message.objects.filter(receiver=request.user).select_related('sender')
    unread = Message.objects.filter(receiver=request.user, is_read=False).count()
    from apps.dashboard.list_helpers import apply_sort, paginate_table, get_filter_querystring

    qs = apply_sort(
        qs,
        request,
        allowed={'created_at': 'created_at', 'sender': 'sender__username', 'receiver': 'receiver__username'},
        default_field='created_at',
        default_dir='desc',
    )
    page, filter_querystring = paginate_table(request, qs)
    compose_form = ComposeMessageForm(sender=request.user)
    return render(
        request,
        'messaging/inbox.html',
        {
            'page_obj': page,
            'box': box,
            'unread_count': unread,
            'compose_form': compose_form,
            'filter_querystring': filter_querystring,
            'sort_by': request.GET.get('sort_by', 'created_at'),
            'sort_dir': request.GET.get('sort_dir', 'desc'),
            'sort_options': [
                ('created_at', 'Date'),
                ('sender', 'Sender'),
                ('receiver', 'Receiver'),
            ],
        },
    )


@login_required
def compose(request):
    from django.urls import reverse
    return redirect(reverse('messaging:inbox') + '?compose=1')


@login_required
@require_POST
def mark_read(request, pk):
    message = Message.objects.filter(pk=pk).filter(Q(receiver=request.user) | Q(sender=request.user)).first()
    if message and message.receiver_id == request.user.id:
        message.is_read = True
        message.save(update_fields=['is_read'])
    return redirect('messaging:inbox')
