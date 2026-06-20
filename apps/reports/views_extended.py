"""Extended views: audit log, leaderboard, comparisons, tracking, extensions, print, pin."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.decorators import role_required
from apps.accounts.infrastructure.models import User
from apps.reports.teacher_helpers import reports_for_teacher_q
from apps.accounts.permissions import user_can_pin_reports, user_can_review_extension

from .forms import ActivityLogFilterForm, DeadlineExtensionRequestForm
from .models import (
    ActivityLog,
    DeadlineExtensionRequest,
    Report,
    ReportVersion,
    SystemSettings,
)


def _apply_activity_filters(qs, form):
    if not form.is_valid():
        return qs
    user_search_query = form.cleaned_data.get('user_search', '').strip()
    if user_search_query:
        qs = qs.filter(user__username__icontains=user_search_query)
    action_filter = form.cleaned_data.get('action')
    if action_filter:
        qs = qs.filter(action=action_filter)
    date_from = form.cleaned_data.get('date_from')
    date_to = form.cleaned_data.get('date_to')
    if date_from:
        qs = qs.filter(timestamp__date__gte=date_from)
    if date_to:
        qs = qs.filter(timestamp__date__lte=date_to)
    search_query = form.cleaned_data.get('search', '').strip()
    if search_query:
        qs = qs.filter(detail__icontains=search_query)
    return qs


@login_required
@role_required(User.Role.ADMIN)
def activity_log_viewer(request):
    qs = ActivityLog.objects.select_related('user', 'report').order_by('-timestamp')
    form = ActivityLogFilterForm(request.GET or None)
    qs = _apply_activity_filters(qs, form)
    from apps.dashboard.list_helpers import apply_sort, paginate_table, get_filter_querystring

    qs = apply_sort(
        qs,
        request,
        allowed={
            'timestamp': 'timestamp',
            'action': 'action',
            'user': 'user__username',
        },
        default_field='timestamp',
        default_dir='desc',
    )
    page, filter_querystring = paginate_table(request, qs)
    return render(
        request,
        'reports/activity_log.html',
        {
            'page_obj': page,
            'filter_form': form,
            'filter_querystring': filter_querystring,
            'sort_by': request.GET.get('sort_by', 'timestamp'),
            'sort_dir': request.GET.get('sort_dir', 'desc'),
            'sort_options': [
                ('timestamp', 'When'),
                ('action', 'Action'),
                ('user', 'User'),
            ],
        },
    )


@login_required
def leaderboard(request):
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER, User.Role.STUDENT):
        raise Http404()
    qs = Report.objects.filter(
        status=Report.Status.APPROVED,
        is_deleted=False,
        marks__isnull=False,
    ).select_related('student')
    if request.user.role == User.Role.TEACHER:
        qs = qs.filter(reports_for_teacher_q(request.user))
    elif request.user.role == User.Role.STUDENT:
        dept = (request.user.department or '').strip()
        if dept:
            qs = qs.filter(student__department__iexact=dept)
        else:
            qs = qs.filter(student=request.user)
    dept = request.GET.get('dept', '').strip()
    if dept:
        qs = qs.filter(student__department__icontains=dept)
    reports = list(qs.order_by('-marks')[:50])
    return render(request, 'reports/leaderboard.html', {'reports': reports, 'dept_filter': dept})


@login_required
def version_compare(request, pk):
    report = get_object_or_404(Report, pk=pk)
    from .views import _can_view_report

    if not _can_view_report(request.user, report):
        raise Http404()
    v1_id = request.GET.get('v1')
    v2_id = request.GET.get('v2')
    v1 = get_object_or_404(ReportVersion, pk=v1_id, report=report) if v1_id else None
    v2 = get_object_or_404(ReportVersion, pk=v2_id, report=report) if v2_id else None
    versions = report.versions.all()
    return render(
        request,
        'reports/version_compare.html',
        {'report': report, 'v1': v1, 'v2': v2, 'versions': versions},
    )


@login_required
@role_required(User.Role.ADMIN)
def submission_tracking(request):
    """Students who submitted vs pending (no report yet)."""
    students = list(User.objects.filter(role=User.Role.STUDENT, is_active=True))
    has_report = Report.objects.filter(is_deleted=False).values('student_id').distinct()
    has_ids = {r['student_id'] for r in has_report}
    submitted = [s for s in students if s.id in has_ids]
    pending = [s for s in students if s.id not in has_ids]
    return render(
        request,
        'reports/submission_tracking.html',
        {'submitted': submitted, 'pending': pending},
    )


@login_required
@role_required(User.Role.TEACHER)
def teacher_workload(request):
    teacher_assigned_reports = Report.objects.filter(reports_for_teacher_q(request.user), is_deleted=False)
    approved_count = teacher_assigned_reports.filter(status=Report.Status.APPROVED).count()
    pending_review_count = teacher_assigned_reports.filter(status=Report.Status.PENDING, teacher_approved=False).count()
    awaiting_admin_count = teacher_assigned_reports.filter(
        teacher_approved=True, admin_approved=False, status=Report.Status.PENDING
    ).count()
    return render(
        request,
        'reports/teacher_workload.html',
        {
            'total': teacher_assigned_reports.count(),
            'done': approved_count,
            'pending_review': pending_review_count,
            'awaiting_admin': awaiting_admin_count,
        },
    )


@login_required
@role_required(User.Role.STUDENT)
@require_POST
def request_deadline_extension(request, pk):
    report = get_object_or_404(Report, pk=pk)
    from .views import _student_can_act_on_report

    if not _student_can_act_on_report(request.user, report):
        raise Http404()
    if DeadlineExtensionRequest.objects.filter(
        report=report,
        student=request.user,
        status=DeadlineExtensionRequest.Status.PENDING,
    ).exists():
        messages.warning(request, 'You already have a pending extension request.')
        return redirect('reports:detail', pk=pk)
    form = DeadlineExtensionRequestForm(request.POST)
    if form.is_valid():
        DeadlineExtensionRequest.objects.create(
            report=report,
            student=request.user,
            reason=form.cleaned_data['reason'],
        )
        messages.success(request, 'Extension request submitted.')
    else:
        messages.error(request, 'Invalid request.')
    return redirect('reports:detail', pk=pk)


@login_required
@role_required(User.Role.ADMIN)
def extension_queue(request):
    qs = DeadlineExtensionRequest.objects.filter(status=DeadlineExtensionRequest.Status.PENDING).select_related(
        'report', 'student'
    )
    return render(request, 'reports/extension_queue.html', {'requests': qs})


@login_required
@role_required(User.Role.ADMIN)
@require_POST
def extension_resolve(request, pk):
    if not user_can_review_extension(request.user):
        raise Http404()
    extension_request = get_object_or_404(DeadlineExtensionRequest, pk=pk)
    decision = request.POST.get('decision')
    note = request.POST.get('note', '')[:500]
    if decision not in ('approve', 'reject'):
        messages.error(request, 'Invalid decision.')
        return redirect('reports:extension_queue')
    extension_request.status = (
        DeadlineExtensionRequest.Status.APPROVED
        if decision == 'approve'
        else DeadlineExtensionRequest.Status.REJECTED
    )
    extension_request.reviewed_by = request.user
    extension_request.admin_note = note
    extension_request.resolved_at = timezone.now()
    extension_request.save()
    if decision == 'approve' and extension_request.report:
        from datetime import timedelta

        system_settings = SystemSettings.get_settings()
        system_settings.submission_deadline = system_settings.submission_deadline + timedelta(days=7)
        system_settings.save(update_fields=['submission_deadline'])
        messages.success(request, 'Extension approved — deadline extended by 7 days (global).')
    else:
        messages.info(request, 'Extension request rejected.')
    return redirect('reports:extension_queue')


@login_required
@role_required(User.Role.ADMIN)
@require_POST
def toggle_pin_report(request, pk):
    if not user_can_pin_reports(request.user):
        raise Http404()
    report = get_object_or_404(Report, pk=pk)
    report.is_pinned = not report.is_pinned
    report.save(update_fields=['is_pinned'])
    messages.success(request, 'Pinned state updated.')
    return redirect('reports:detail', pk=pk)


@login_required
def report_print(request, pk):
    report = get_object_or_404(Report.objects.select_related('student'), pk=pk)
    from .views import _can_view_report

    if not _can_view_report(request.user, report):
        raise Http404()
    return render(request, 'reports/report_print.html', {'report': report})
