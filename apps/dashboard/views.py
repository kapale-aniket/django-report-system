import calendar
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncMonth
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.accounts.decorators import role_required
from apps.accounts.infrastructure.models import User
from apps.reports.teacher_helpers import reports_for_teacher_q

from apps.reports.forms import CertificateTemplateForm, DeadlineForm
from apps.reports.infrastructure.models import (
    Announcement,
    CertificateTemplate,
    DeadlineExtensionRequest,
    Report,
    ReportRecentView,
    SystemSettings,
)

from apps.qa.forms import VisitorQuestionForm
from apps.qa.infrastructure.models import FAQ, UserQuestion, VisitorQuestion
from core.utils.user_messages import friendly_message


def landing(request):
    """Marketing home; signed-in users skip to their dashboard."""
    if request.user.is_authenticated:
        return redirect('accounts:post_login_redirect')

    landing_faqs = FAQ.objects.filter(is_active=True)
    if request.method == 'POST' and 'visitor_ask_submit' in request.POST:
        visitor_form = VisitorQuestionForm(request.POST)
        if visitor_form.is_valid():
            visitor_form.save()
            messages.success(
                request,
                'Thanks — your question was received. An administrator will reply by email.',
            )
            return HttpResponseRedirect(reverse('dashboard:landing') + '#qa')
    else:
        visitor_form = VisitorQuestionForm()

    return render(
        request,
        'landing.html',
        {
            'visitor_form': visitor_form,
            'landing_faqs': landing_faqs,
        },
    )


def _six_month_window():
    """Start/end month datetimes, display labels, and YYYY-MM keys for the last 6 calendar months."""
    now = timezone.now()
    end_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start = end_month
    for _ in range(5):
        if start.month == 1:
            start = start.replace(year=start.year - 1, month=12)
        else:
            start = start.replace(month=start.month - 1)

    labels = []
    keys = []
    cur = start
    while cur <= end_month:
        labels.append(cur.strftime('%b %Y'))
        keys.append(cur.strftime('%Y-%m'))
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)

    range_from = start.date()
    range_to = now.date()
    return start, end_month, keys, labels, range_from, range_to


def _monthly_submissions_last_6_months(base_qs=None):
    """Labels and counts for Chart.js (last 6 calendar months from start of current month -5)."""
    start, _, keys, labels, _, _ = _six_month_window()
    qs = (base_qs or Report.objects.filter(is_deleted=False)).filter(submitted_at__gte=start)

    rows = (
        qs.annotate(month=TruncMonth('submitted_at'))
        .values('month')
        .annotate(total=Count('id'))
        .order_by('month')
    )
    by_month = {row['month'].strftime('%Y-%m'): row['total'] for row in rows if row['month']}
    values = [by_month.get(key, 0) for key in keys]
    return labels, values, keys


def _monthly_approved_pending(base_qs=None):
    """Same 6-month window as submissions; counts approved vs pending per month."""
    start, _, keys, labels, range_from, range_to = _six_month_window()
    qs = (base_qs or Report.objects.filter(is_deleted=False)).filter(submitted_at__gte=start)

    rows = (
        qs.annotate(month=TruncMonth('submitted_at'))
        .values('month')
        .annotate(
            approved=Count('id', filter=Q(status=Report.Status.APPROVED)),
            pending=Count('id', filter=Q(status=Report.Status.PENDING)),
        )
        .order_by('month')
    )
    by_month = {}
    for row in rows:
        if row['month']:
            key = row['month'].strftime('%Y-%m')
            by_month[key] = (row['approved'], row['pending'])

    approved_vals = []
    pending_vals = []
    for key in keys:
        pair = by_month.get(key, (0, 0))
        approved_vals.append(pair[0])
        pending_vals.append(pair[1])
    return labels, approved_vals, pending_vals, range_from, range_to


def _month_date_bounds(month_key: str) -> tuple[str, str]:
    """Return ISO date_from and date_to for a YYYY-MM month key."""
    year, month = (int(part) for part in month_key.split('-'))
    last_day = calendar.monthrange(year, month)[1]
    return f'{month_key}-01', f'{month_key}-{last_day:02d}'


@login_required
@role_required(User.Role.ADMIN)
def admin_dashboard(request):
    from application.services.certificate_template_service import CertificateTemplateService

    settings_obj = SystemSettings.get_settings()
    deadline_form = DeadlineForm(instance=settings_obj)
    cert_service = CertificateTemplateService()
    cert_templates = cert_service.list_templates()

    edit_id = request.GET.get('cert_template')
    new_template = request.GET.get('new_template')
    if edit_id:
        cert_template = get_object_or_404(CertificateTemplate, pk=edit_id)
    elif new_template:
        cert_template = CertificateTemplate(is_active=False, name='New certificate template')
    else:
        cert_template = CertificateTemplate.get_active()
    certificate_template_form = CertificateTemplateForm(instance=cert_template)

    if request.method == 'POST' and 'save_deadline' in request.POST:
        deadline_form = DeadlineForm(request.POST, instance=settings_obj)
        if deadline_form.is_valid():
            deadline_form.save()
            messages.success(request, 'System settings updated.')
            return redirect('dashboard:admin_dashboard')

    if request.method == 'POST' and 'activate_certificate_template' in request.POST:
        template_id = request.POST.get('template_id')
        try:
            cert_service.activate_template(request.user, int(template_id))
            messages.success(request, 'Certificate template set as active for all new certificates.')
        except Exception as exc:
            messages.error(request, friendly_message(exc, fallback='Could not activate template.'))
        return redirect('dashboard:admin_dashboard')

    if request.method == 'POST' and 'save_certificate_template' in request.POST:
        template_pk = request.POST.get('template_pk')
        instance = cert_template
        if template_pk:
            instance = get_object_or_404(CertificateTemplate, pk=template_pk)
        elif request.POST.get('create_new_template') == '1':
            instance = CertificateTemplate(is_active=False)

        certificate_template_form = CertificateTemplateForm(
            request.POST,
            request.FILES,
            instance=instance,
        )
        if certificate_template_form.is_valid():
            activate = request.POST.get('set_active_on_save', '1') == '1'
            saved = cert_service.save_from_form(
                request.user,
                certificate_template_form,
                activate=activate,
            )
            messages.success(
                request,
                f'Certificate template "{saved.name}" saved.'
                + (' It is now active for all new certificates.' if saved.is_active else ''),
            )
            return redirect('dashboard:admin_dashboard')

    total_students = User.objects.filter(role=User.Role.STUDENT).count()
    total_teachers = User.objects.filter(role=User.Role.TEACHER).count()
    awaiting_admin = Report.objects.filter(
        is_deleted=False,
        status=Report.Status.PENDING,
        teacher_approved=True,
        admin_approved=False,
    ).count()
    pending_users = User.objects.filter(is_active=False).exclude(role=User.Role.ADMIN).count()
    open_user_questions = UserQuestion.objects.filter(status=UserQuestion.Status.OPEN).count()
    open_visitor_questions = VisitorQuestion.objects.filter(status=VisitorQuestion.Status.OPEN).count()
    open_qa_count = open_user_questions + open_visitor_questions
    pending_extensions = DeadlineExtensionRequest.objects.filter(
        status=DeadlineExtensionRequest.Status.PENDING
    ).count()
    total_reports = Report.objects.filter(is_deleted=False).count()
    approved_reports = Report.objects.filter(is_deleted=False, status=Report.Status.APPROVED).count()

    announcements = list(
        Announcement.objects.filter(is_active=True)
        .filter(Q(target_role=Announcement.TargetRole.ALL) | Q(target_role=User.Role.ADMIN))
        .order_by('-created_at')[:5]
    )

    return render(
        request,
        'dashboard/admin_dashboard.html',
        {
            'total_students': total_students,
            'total_teachers': total_teachers,
            'awaiting_admin': awaiting_admin,
            'pending_users': pending_users,
            'open_qa_count': open_qa_count,
            'pending_extensions': pending_extensions,
            'total_reports': total_reports,
            'approved_reports': approved_reports,
            'deadline_form': deadline_form,
            'deadline': settings_obj.submission_deadline,
            'max_attempts': settings_obj.max_attempts,
            'max_file_size_mb': settings_obj.max_file_size_mb,
            'group_deadline': settings_obj.group_submission_deadline or settings_obj.submission_deadline,
            'group_max_attempts': settings_obj.group_max_attempts,
            'group_min_members': settings_obj.group_min_members,
            'group_max_members': settings_obj.group_max_members,
            'announcements': announcements,
            'cert_template': cert_template,
            'cert_templates': cert_templates,
            'certificate_template_form': certificate_template_form,
            'editing_new_template': bool(new_template),
        },
    )


@login_required
@role_required(User.Role.TEACHER)
def teacher_dashboard(request):
    rq = Report.objects.filter(reports_for_teacher_q(request.user), is_deleted=False)
    all_reports = rq.count()
    pending_teacher = rq.filter(
        status=Report.Status.PENDING,
        teacher_approved=False,
    ).count()

    awaiting_admin = rq.filter(
        teacher_approved=True,
        admin_approved=False,
        status=Report.Status.PENDING,
    ).count()
    rejected_all = rq.filter(status=Report.Status.REJECTED).count()
    approved_all = rq.filter(status=Report.Status.APPROVED).count()

    chart_labels, chart_values, chart_month_keys = _monthly_submissions_last_6_months(rq)
    _, chart_approved, chart_pending, chart_range_from, chart_range_to = _monthly_approved_pending(rq)
    chart_month_urls = [
        reverse('reports:list')
        + f'?date_from={_month_date_bounds(key)[0]}&date_to={_month_date_bounds(key)[1]}'
        for key in chart_month_keys
    ]
    announcements = list(
        Announcement.objects.filter(is_active=True)
        .filter(Q(target_role=Announcement.TargetRole.ALL) | Q(target_role=User.Role.TEACHER))
        .order_by('-created_at')[:5]
    )

    return render(
        request,
        'dashboard/teacher_dashboard.html',
        {
            'assigned_reports': all_reports,
            'pending_teacher': pending_teacher,
            'awaiting_admin': awaiting_admin,
            'rejected_all': rejected_all,
            'approved_all': approved_all,
            'chart_labels_json': json.dumps(chart_labels),
            'chart_values_json': json.dumps(chart_values),
            'chart_month_keys_json': json.dumps(chart_month_keys),
            'chart_month_urls_json': json.dumps(chart_month_urls),
            'chart_approved_json': json.dumps(chart_approved),
            'chart_pending_json': json.dumps(chart_pending),
            'chart_range_from': chart_range_from.isoformat(),
            'chart_range_to': chart_range_to.isoformat(),
            'reports_list_url': reverse('reports:list'),
            'announcements': announcements,
        },
    )


@login_required
@role_required(User.Role.STUDENT)
def student_dashboard(request):
    base = Report.objects.filter(student=request.user, is_deleted=False)
    recent = base.order_by('-submitted_at')[:5]
    pending = base.filter(status=Report.Status.PENDING).count()
    approved = base.filter(status=Report.Status.APPROVED).count()
    rejected = base.filter(status=Report.Status.REJECTED).count()
    total_reports = base.count()

    ranked = list(
        User.objects.filter(role=User.Role.STUDENT)
        .annotate(
            avg_marks=Avg(
                'reports__marks',
                filter=Q(
                    reports__status=Report.Status.APPROVED,
                    reports__is_deleted=False,
                    reports__marks__isnull=False,
                ),
            )
        )
        .order_by('-avg_marks', 'username')
    )
    total_students_ranked = len(ranked)
    student_rank = None
    for i, u in enumerate(ranked, start=1):
        if u.id == request.user.id:
            student_rank = i
            break
    if student_rank is None:
        student_rank = '—'

    recently_viewed = [
        rv.report
        for rv in ReportRecentView.objects.filter(user=request.user).select_related('report')[:8]
        if not rv.report.is_deleted
    ]
    announcements = list(
        Announcement.objects.filter(is_active=True)
        .filter(Q(target_role=Announcement.TargetRole.ALL) | Q(target_role=User.Role.STUDENT))
        .order_by('-created_at')[:5]
    )

    from apps.reports.certificate_celebration import get_pending_certificate_celebration

    certificate_celebration = get_pending_certificate_celebration(request.user)
    certificate_celebration_json = json.dumps(certificate_celebration) if certificate_celebration else ''

    return render(
        request,
        'dashboard/student_dashboard.html',
        {
            'recent_reports': recent,
            'pending_count': pending,
            'approved_count': approved,
            'rejected_count': rejected,
            'total_reports': total_reports,
            'student_rank': student_rank,
            'total_students_ranked': total_students_ranked,
            'recently_viewed': recently_viewed,
            'announcements': announcements,
            'certificate_celebration': certificate_celebration,
            'certificate_celebration_json': certificate_celebration_json,
        },
    )
