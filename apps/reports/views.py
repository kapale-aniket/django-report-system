import csv
import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Max, Q
from django.core.files.base import ContentFile
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.decorators import role_required
from apps.accounts.infrastructure.models import User

from .constants import report_content_type
from .forms import (
    ActivityLogFilterForm,
    AdminFinalMarksForm,
    CommentForm,
    DeadlineExtensionRequestForm,
    ReEvaluationRequestForm,
    ReportFilterForm,
    ReportResubmitForm,
    ReportSubmitForm,
    TeacherEvaluationForm,
)
from .models import (
    ActivityLog,
    Announcement,
    CertificateTemplate,
    Comment,
    DeadlineExtensionRequest,
    Notification,
    ReEvaluationRequest,
    Report,
    ReportBookmark,
    ReportRecentView,
    ReportVersion,
    Rubric,
    SystemSettings,
)
from .group_helpers import (
    get_department_students,
    get_teachers_for_department,
    notify_group_submission_stakeholders,
    notify_report_stakeholders_sync,
    notify_teacher_for_report_submission,
    sync_group_report_teacher,
    teacher_display_with_department,
)
from .settings_helpers import (
    get_group_project_rules,
    get_individual_project_rules,
    get_max_attempts_for_report,
    get_submission_deadline_for_report,
)
from application.services.project_group_service import ProjectGroupService
from .teacher_helpers import get_report_assigned_teacher, reports_for_teacher_q, teacher_can_access_report
from .notifications import create_in_app_notification
from .certificate_helpers import notify_admin_final_approval
from .comment_helpers import post_report_comment, staff_comments_for_report
from .utils import (
    log_activity,
    send_rejection_email,
)
from tasks.dispatch import queue_report_submitted_email, queue_teacher_approved_email
from core.utils.user_messages import friendly_message


def _mark_late_on_create(report):
    deadline = get_submission_deadline_for_report(report)
    if report.submitted_at and deadline:
        report.is_late_submission = report.submitted_at > deadline
        report.save(update_fields=['is_late_submission'])


def _mark_late_resubmit(report):
    deadline = get_submission_deadline_for_report(report)
    report.is_late_submission = timezone.now() > deadline if deadline else False
    report.save(update_fields=['is_late_submission'])


def _student_can_act_on_report(user, report):
    """Submitter or member of the same project group."""
    if report.student_id == user.id:
        return True
    if report.group_id and report.group.members.filter(pk=user.pk).exists():
        return True
    return False


def _can_view_report(user, report):
    if report.is_deleted:
        if user.role == User.Role.ADMIN:
            return True
        return False
    if user.role == User.Role.ADMIN:
        return True
    if user.role == User.Role.TEACHER:
        return teacher_can_access_report(user, report)
    if user.role == User.Role.STUDENT:
        return _student_can_act_on_report(user, report)
    return False


def _student_report_membership_q(student) -> Q:
    """Reports owned by the student or group projects they belong to."""
    return Q(student=student) | Q(group__members=student)


def _can_view_student_full_profile(user, student) -> bool:
    if not getattr(user, 'is_authenticated', False):
        return False
    if user.role == User.Role.ADMIN:
        return True
    if user.role == User.Role.TEACHER:
        teacher_q = reports_for_teacher_q(user)
        membership_q = _student_report_membership_q(student)
        return Report.objects.filter(is_deleted=False).filter(membership_q).filter(teacher_q).exists()
    if user.role == User.Role.STUDENT:
        return user.pk == student.pk
    return False


def _ordered_group_members(report) -> list:
    """Group members for review UI — submitter first, then alphabetical."""
    if not report.group_id:
        return []
    members = list(
        report.group.members.select_related('assigned_teacher').order_by('first_name', 'username')
    )
    submitter_id = report.student_id

    def sort_key(member):
        return (0 if member.pk == submitter_id else 1, (member.first_name or '').lower(), member.username.lower())

    return sorted(members, key=sort_key)


def _safe_back_url(request) -> str | None:
    next_url = (request.GET.get('next') or '').strip()
    if next_url.startswith('/') and not next_url.startswith('//'):
        return next_url
    return None


def _default_student_profile_back_url(request) -> str:
    if getattr(request.user, 'is_authenticated', False):
        role = getattr(request.user, 'role', None)
        if role == User.Role.TEACHER:
            return reverse('reports:list')
        if role == User.Role.ADMIN:
            return reverse('accounts:user_management')
        if role == User.Role.STUDENT:
            return reverse('reports:my_reports')
    return reverse('dashboard:landing')


@login_required
@role_required(User.Role.STUDENT)
def submit_report(request):
    group_service = ProjectGroupService()
    submittable_groups = group_service.submittable_groups_for_user(request.user)
    if request.method == 'POST':
        form = ReportSubmitForm(
            request.POST,
            request.FILES,
            user=request.user,
            submittable_groups=submittable_groups,
        )
        if form.is_valid():
            report = form.save(commit=False)
            report.student = request.user
            report.submission_round = Report.SubmissionRound.REVIEW
            report.attempt_count = 1
            rubric = Rubric.objects.filter(is_default=True, is_active=True).first()
            report.rubric = rubric
            if form.cleaned_data.get('submission_type') == ReportSubmitForm.SUBMISSION_GROUP:
                report.group = form.cleaned_data['project_group']
                report.assigned_teacher_id = report.group.assigned_teacher_id
            elif request.user.assigned_teacher_id:
                report.assigned_teacher_id = request.user.assigned_teacher_id
            report.save()
            _mark_late_on_create(report)
            log_activity(request.user, ActivityLog.Action.SUBMITTED, report)
            if report.group_id:
                notify_group_submission_stakeholders(report, submitter=request.user)
            else:
                notify_report_stakeholders_sync(
                    report,
                    f'Your report "{report.title}" was submitted successfully.',
                    link=f'/reports/{report.pk}/',
                )
                notify_teacher_for_report_submission(report, submitter=request.user)
            queue_report_submitted_email(report.pk)
            messages.success(request, 'Report submitted successfully.')
            return redirect('reports:my_reports')
    else:
        form = ReportSubmitForm(user=request.user, submittable_groups=submittable_groups)
    settings_obj = SystemSettings.get_settings()
    ctx = {
        'form': form,
        'settings': settings_obj,
        'submittable_groups': submittable_groups,
        'individual_rules': get_individual_project_rules(settings_obj),
        'group_rules': get_group_project_rules(settings_obj),
    }
    return render(request, 'reports/submit.html', ctx)


@login_required
@role_required(User.Role.STUDENT)
def my_reports(request):
    qs = Report.objects.filter(is_deleted=False).filter(
        Q(student=request.user) | Q(group__members=request.user)
    ).distinct()
    form = ReportFilterForm(request.GET or None)
    if form.is_valid():
        status_filter = form.cleaned_data.get('status', '')
        if status_filter == Report.Status.PENDING:
            qs = qs.filter(status=Report.Status.PENDING)
        elif status_filter == Report.Status.APPROVED:
            qs = qs.filter(status=Report.Status.APPROVED)
        elif status_filter == Report.Status.REJECTED:
            qs = qs.filter(status=Report.Status.REJECTED)
        elif status_filter == 'awaiting_admin':
            qs = qs.filter(
                teacher_approved=True,
                admin_approved=False,
                status=Report.Status.PENDING,
            )
        elif status_filter == 'late':
            qs = qs.filter(is_late_submission=True)
    from apps.dashboard.list_helpers import apply_sort, paginate_table, get_filter_querystring

    qs = apply_sort(
        qs,
        request,
        allowed={'submitted_at': 'submitted_at', 'title': 'title', 'status': 'status'},
        default_field='submitted_at',
        default_dir='desc',
    )
    page, filter_querystring = paginate_table(request, qs)
    return render(
        request,
        'reports/my_reports.html',
        {
            'page_obj': page,
            'filter_form': form,
            'filter_querystring': filter_querystring,
            'sort_by': request.GET.get('sort_by', 'submitted_at'),
            'sort_dir': request.GET.get('sort_dir', 'desc'),
            'sort_options': [
                ('submitted_at', 'Submitted date'),
                ('title', 'Title'),
                ('status', 'Status'),
            ],
        },
    )


@login_required
def report_detail(request, pk):
    report = get_object_or_404(
        Report.objects.select_related(
            'student',
            'student__assigned_teacher',
            'assigned_teacher',
            'group',
            'group__assigned_teacher',
            'rubric',
        ).prefetch_related('comments__user', 'group__members'),
        pk=pk,
    )
    if not _can_view_report(request.user, report):
        raise Http404()
    _rv, rv_created = ReportRecentView.objects.get_or_create(user=request.user, report=report)
    if not rv_created:
        ReportRecentView.objects.filter(pk=_rv.pk).update(viewed_at=timezone.now())
    comment_form = CommentForm()
    resubmit_form = ReportResubmitForm()
    teacher_eval_form = TeacherEvaluationForm(
        initial={
            'teacher_marks': report.teacher_marks,
            'feedback': report.feedback,
            'is_final_submission': report.is_final_submission,
        }
    )
    admin_marks_form = AdminFinalMarksForm(initial={'marks': report.teacher_marks if report.teacher_marks is not None else 0})
    reeval_form = ReEvaluationRequestForm()
    versions = report.versions.all()[:20]
    timeline = report.activity_logs.select_related('user').all()[:50]
    bookmarked = False
    if request.user.is_authenticated:
        bookmarked = ReportBookmark.objects.filter(user=request.user, report=report).exists()

    can_comment = (
        request.user.role in (User.Role.TEACHER, User.Role.ADMIN)
        or (
            request.user.role == User.Role.STUDENT
            and report.student_id == request.user.id
        )
    ) and not report.is_locked

    can_resubmit = (
        request.user.role == User.Role.STUDENT
        and _student_can_act_on_report(request.user, report)
        and report.status == Report.Status.REJECTED
        and not report.is_locked
        and report.attempt_count < get_max_attempts_for_report(report)
    )

    can_download_certificate = False
    if report.is_certificate_eligible:
        if request.user.role == User.Role.ADMIN:
            can_download_certificate = True
        elif request.user.role == User.Role.TEACHER and teacher_can_access_report(request.user, report):
            can_download_certificate = True
        elif request.user.role == User.Role.STUDENT and _student_can_act_on_report(request.user, report):
            can_download_certificate = True

    pending_reeval = None
    if request.user.role == User.Role.STUDENT:
        pending_reeval = ReEvaluationRequest.objects.filter(
            report=report, student=request.user, status=ReEvaluationRequest.Status.PENDING
        ).first()

    reeval_admin_queue = []
    if request.user.role == User.Role.ADMIN:
        reeval_admin_queue = list(
            ReEvaluationRequest.objects.filter(
                report=report, status=ReEvaluationRequest.Status.PENDING
            ).select_related('student')
        )

    rubric_rows = []
    if report.rubric_id:
        scores = report.rubric_scores_json or {}
        for c in report.rubric.iter_criteria():
            rubric_rows.append(
                {
                    'criterion': c,
                    'score': int(scores.get(str(c.pk), scores.get(c.pk, 0))),
                    'max_score': c.max_score,
                }
            )

    announcements = list(
        Announcement.objects.filter(is_active=True)
        .filter(Q(target_role=Announcement.TargetRole.ALL) | Q(target_role=getattr(request.user, 'role', '')))
        .order_by('-created_at')[:8]
    )

    extension_form = DeadlineExtensionRequestForm()
    pending_extension = None
    if request.user.role == User.Role.STUDENT and _student_can_act_on_report(request.user, report):
        pending_extension = DeadlineExtensionRequest.objects.filter(
            report=report,
            student=request.user,
            status=DeadlineExtensionRequest.Status.PENDING,
        ).first()

    if request.user.role == User.Role.ADMIN:
        if report.group_id:
            report_teachers = get_teachers_for_department(report.group.department)
        else:
            report_teachers = User.objects.filter(role=User.Role.TEACHER, is_active=True).order_by('username')
    else:
        report_teachers = User.objects.none()

    user_certificate_code = None
    if can_download_certificate and report.is_certificate_eligible:
        from application.services.certificate_service import CertificateService

        user_certificate_code = CertificateService().verification_code_for_user(report, request.user)

    return render(
        request,
        'reports/detail.html',
        {
            'report': report,
            'comment_form': comment_form,
            'resubmit_form': resubmit_form,
            'teacher_eval_form': teacher_eval_form,
            'admin_marks_form': admin_marks_form,
            'reeval_form': reeval_form,
            'versions': versions,
            'timeline': timeline,
            'bookmarked': bookmarked,
            'can_comment': can_comment,
            'can_resubmit': can_resubmit,
            'can_download_certificate': can_download_certificate,
            'pending_reeval': pending_reeval,
            'reeval_admin_queue': reeval_admin_queue,
            'settings': SystemSettings.get_settings(),
            'report_max_attempts': get_max_attempts_for_report(report),
            'rubric_rows': rubric_rows,
            'announcements': announcements,
            'extension_form': extension_form,
            'pending_extension': pending_extension,
            'staff_comments': staff_comments_for_report(report),
            'report_teachers': report_teachers,
            'report_assigned_teacher': get_report_assigned_teacher(report),
            'group_assigned_teacher_label': (
                teacher_display_with_department(report.group.assigned_teacher)
                if report.group_id and report.group.assigned_teacher_id
                else ''
            ),
            'user_certificate_code': user_certificate_code,
        },
    )


@login_required
def report_group_member_profiles(request, pk):
    """List all group project members with links to each student profile."""
    report = get_object_or_404(
        Report.objects.select_related('student', 'group').prefetch_related('group__members'),
        pk=pk,
    )
    if not report.group_id or not _can_view_report(request.user, report):
        raise Http404()

    back_url = _safe_back_url(request) or reverse('reports:detail', kwargs={'pk': report.pk})
    return render(
        request,
        'reports/group_member_profiles.html',
        {
            'report': report,
            'group_members': _ordered_group_members(report),
            'back_url': back_url,
            'back_label': 'Back to report',
            'staff_view': request.user.role in (User.Role.TEACHER, User.Role.ADMIN),
        },
    )


@login_required
@role_required(User.Role.STUDENT)
@require_POST
def certificate_celebration_ack(request, pk):
    from apps.reports.certificate_celebration import acknowledge_certificate_celebration

    report = get_object_or_404(Report, pk=pk)
    if not _student_can_act_on_report(request.user, report):
        raise Http404()
    if not report.certificate_generated or not report.is_certificate_eligible:
        return JsonResponse(
            {'success': False, 'message': 'Certificate celebration is not available for this report.'},
            status=400,
        )
    acknowledge_certificate_celebration(request.user, report)
    return JsonResponse({'success': True, 'message': 'Celebration marked as viewed.'})


@login_required
def view_pdf(request, pk):
    report = get_object_or_404(Report, pk=pk)
    if not _can_view_report(request.user, report):
        raise Http404()
    if not report.file:
        raise Http404()
    filename = report.file.name.split('/')[-1]
    content_type = report_content_type(filename)
    file_response = FileResponse(report.file.open('rb'), content_type=content_type)
    disposition = 'inline' if report.is_pdf_file else 'attachment'
    file_response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
    return file_response


def _apply_report_filters(qs, form):
    if not form.is_valid():
        return qs
    search_query = form.cleaned_data.get('search', '').strip()
    status_filter = form.cleaned_data.get('status', '')
    department_filter = form.cleaned_data.get('department', '').strip()
    min_marks = form.cleaned_data.get('min_marks')
    max_marks = form.cleaned_data.get('max_marks')
    date_from = form.cleaned_data.get('date_from')
    date_to = form.cleaned_data.get('date_to')
    include_deleted = form.cleaned_data.get('include_deleted')

    if not include_deleted:
        qs = qs.filter(is_deleted=False)
    if search_query:
        qs = qs.filter(
            Q(title__icontains=search_query)
            | Q(student__username__icontains=search_query)
            | Q(student__first_name__icontains=search_query)
            | Q(student__last_name__icontains=search_query)
            | Q(tags__icontains=search_query)
        )
    if department_filter:
        qs = qs.filter(student__department__icontains=department_filter)
    if status_filter == Report.Status.PENDING:
        qs = qs.filter(status=Report.Status.PENDING)
    elif status_filter == Report.Status.APPROVED:
        qs = qs.filter(status=Report.Status.APPROVED)
    elif status_filter == Report.Status.REJECTED:
        qs = qs.filter(status=Report.Status.REJECTED)
    elif status_filter == 'awaiting_admin':
        qs = qs.filter(
            teacher_approved=True,
            admin_approved=False,
            status=Report.Status.PENDING,
        )
    elif status_filter == 'awaiting_teacher':
        qs = qs.filter(
            teacher_approved=False,
            status=Report.Status.PENDING,
        )
    elif status_filter == 'late':
        qs = qs.filter(is_late_submission=True)
    elif status_filter:
        qs = qs.filter(status=status_filter)
    if min_marks is not None:
        qs = qs.filter(marks__gte=min_marks)
    if max_marks is not None:
        qs = qs.filter(marks__lte=max_marks)
    if date_from:
        qs = qs.filter(submitted_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(submitted_at__date__lte=date_to)
    academic_year_filter = form.cleaned_data.get('academic_year', '').strip()
    if academic_year_filter:
        qs = qs.filter(academic_year__icontains=academic_year_filter)
    if not form.cleaned_data.get('include_archived'):
        qs = qs.filter(is_archived=False)
    return qs


@login_required
def report_list(request):
    if request.user.role not in (User.Role.TEACHER, User.Role.ADMIN):
        raise Http404()

    qs = Report.objects.select_related('student').all().order_by('-submitted_at')
    if request.user.role == User.Role.TEACHER:
        qs = qs.filter(reports_for_teacher_q(request.user))

    form = ReportFilterForm(request.GET or None)
    qs = _apply_report_filters(qs, form)

    from apps.dashboard.list_helpers import apply_sort, paginate_table

    sort_by = request.GET.get('sort_by', 'submitted_at')
    sort_dir = request.GET.get('sort_dir', 'desc')
    qs = apply_sort(
        qs,
        request,
        allowed={
            'submitted_at': 'submitted_at',
            'title': 'title',
            'marks': 'marks',
            'student': 'student__username',
            'status': 'status',
        },
        default_field='submitted_at',
        default_dir='desc',
    )

    page, filter_querystring = paginate_table(request, qs)
    sort_options = [
        ('submitted_at', 'Submitted date'),
        ('title', 'Title'),
        ('marks', 'Marks'),
        ('student', 'Student'),
        ('status', 'Status'),
    ]
    return render(
        request,
        'reports/list.html',
        {
            'page_obj': page,
            'filter_form': form,
            'filter_querystring': filter_querystring,
            'sort_by': sort_by,
            'sort_dir': sort_dir,
            'sort_options': sort_options,
        },
    )


@login_required
@role_required(User.Role.TEACHER)
@require_POST
def teacher_approve(request, pk):
    report = get_object_or_404(Report, pk=pk)
    if not teacher_can_access_report(request.user, report):
        raise Http404()
    if report.status == Report.Status.REJECTED or report.is_locked:
        messages.error(request, 'Cannot approve this report in its current state.')
        return redirect('reports:detail', pk=pk)
    form = TeacherEvaluationForm(request.POST)
    if form.is_valid():
        report.teacher_marks = form.cleaned_data.get('teacher_marks')
        feedback = (form.cleaned_data.get('feedback') or '').strip()
        report.feedback = feedback
        report.is_final_submission = form.cleaned_data.get('is_final_submission', False)
        report.teacher_approved = True
        report.refresh_status_from_flags()
        report.save()
        if feedback:
            post_report_comment(report, request.user, feedback)
        if report.rubric_id:
            stored: dict[str, int] = dict(report.rubric_scores_json or {})
            for crit in report.rubric.iter_criteria():
                key = f'criterion_{crit.pk}'
                if key in request.POST:
                    try:
                        val = max(0, min(int(request.POST.get(key)), crit.max_score))
                    except (TypeError, ValueError):
                        val = 0
                    stored[str(crit.pk)] = val
            report.rubric_scores_json = stored
            report.save(update_fields=['rubric_scores_json'])
        log_activity(request.user, ActivityLog.Action.TEACHER_APPROVED, report)
        notify_report_stakeholders_sync(
            report,
            f'Teacher approved your report "{report.title}". Awaiting admin final approval.',
            link=f'/reports/{report.pk}/',
        )
        queue_teacher_approved_email(report.pk)
        if report.is_final_submission:
            messages.success(
                request,
                'Teacher approval saved. Marked as final submission — certificate will be issued after admin approval.',
            )
        else:
            messages.success(request, 'Teacher approval and evaluation saved.')
    else:
        messages.error(request, 'Check marks (0–100) and feedback.')
    return redirect('reports:detail', pk=pk)


@login_required
@role_required(User.Role.TEACHER)
@require_POST
def teacher_reject(request, pk):
    report = get_object_or_404(Report, pk=pk)
    if not teacher_can_access_report(request.user, report):
        raise Http404()
    reason = request.POST.get('reason', '').strip()
    if not reason:
        messages.error(request, 'Rejection reason is required.')
        return redirect('reports:detail', pk=pk)
    report.teacher_approved = False
    report.admin_approved = False
    report.status = Report.Status.REJECTED
    report.rejection_reason = reason
    report.is_locked = False
    report.submission_round = Report.SubmissionRound.REVIEW
    report.save()
    post_report_comment(report, request.user, reason)
    log_activity(request.user, ActivityLog.Action.TEACHER_REJECTED, report, detail=reason[:500])
    notify_report_stakeholders_sync(
        report,
        f'Your report "{report.title}" was rejected by teacher. Reason sent by email.',
        link=f'/reports/{report.pk}/',
    )
    send_rejection_email(report, reason)
    messages.warning(request, 'Report rejected; student notified.')
    return redirect('reports:detail', pk=pk)


@login_required
@role_required(User.Role.ADMIN)
@require_POST
def admin_approve(request, pk):
    report = get_object_or_404(Report, pk=pk)
    if not report.teacher_approved:
        messages.error(request, 'Admin can approve only after teacher approval.')
        return redirect('reports:detail', pk=pk)
    if report.status == Report.Status.REJECTED:
        messages.error(request, 'Report is rejected.')
        return redirect('reports:detail', pk=pk)
    form = AdminFinalMarksForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Enter final marks (0–100).')
        return redirect('reports:detail', pk=pk)
    report.marks = form.cleaned_data['marks']
    report.admin_approved = True
    report.refresh_status_from_flags()
    report.save()
    log_activity(request.user, ActivityLog.Action.ADMIN_APPROVED, report)
    log_activity(request.user, ActivityLog.Action.MARKS_SET, report, detail=f'Final marks: {report.marks}')
    notify_report_stakeholders_sync(
        report,
        f'Final approval: "{report.title}" — marks {report.marks}.',
        link=f'/reports/{report.pk}/',
    )

    if notify_admin_final_approval(report):
        messages.success(request, 'Final approval saved. Completion certificate emailed to the student.')
    else:
        messages.success(request, 'Final approval saved. The student was notified by email.')
    return redirect('reports:detail', pk=pk)


@login_required
@role_required(User.Role.ADMIN)
@require_POST
def admin_reject(request, pk):
    report = get_object_or_404(Report, pk=pk)
    reason = request.POST.get('reason', '').strip()
    if not reason:
        messages.error(request, 'Rejection reason is required.')
        return redirect('reports:detail', pk=pk)
    report.admin_approved = False
    report.teacher_approved = False
    report.status = Report.Status.REJECTED
    report.rejection_reason = reason
    report.is_locked = False
    report.submission_round = Report.SubmissionRound.REVIEW
    report.save()
    post_report_comment(report, request.user, reason)
    log_activity(request.user, ActivityLog.Action.ADMIN_REJECTED, report, detail=reason[:500])
    notify_report_stakeholders_sync(report, f'Admin rejected "{report.title}".', link=f'/reports/{report.pk}/')
    send_rejection_email(report, reason)
    messages.warning(request, 'Report rejected.')
    return redirect('reports:detail', pk=pk)


@login_required
@role_required(User.Role.STUDENT)
@require_POST
def resubmit_report(request, pk):
    report = get_object_or_404(Report, pk=pk)
    if not _student_can_act_on_report(request.user, report):
        raise Http404()
    if report.status != Report.Status.REJECTED:
        messages.error(request, 'You can only resubmit after rejection.')
        return redirect('reports:detail', pk=pk)
    max_a = get_max_attempts_for_report(report)
    if report.attempt_count >= max_a:
        messages.error(request, f'Maximum submission attempts ({max_a}) reached.')
        return redirect('reports:detail', pk=pk)

    form = ReportResubmitForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, 'Please upload a valid PDF or DOCX within the size limit.')
        return redirect('reports:detail', pk=pk)

    m = report.versions.aggregate(Max('version_number'))['version_number__max']
    next_num = (m or 0) + 1

    with report.file.open('rb') as fh:
        archived = fh.read()
    base_name = report.file.name.rsplit('/', maxsplit=1)[-1]
    rv = ReportVersion(report=report, version_number=next_num)
    rv.file.save(f'v{next_num}_{base_name}', ContentFile(archived), save=True)

    report.file = form.cleaned_data['file']
    report.status = Report.Status.PENDING
    report.teacher_approved = False
    report.admin_approved = False
    report.rejection_reason = ''
    report.certificate_generated = False
    report.is_final_submission = False
    report.attempt_count += 1
    report.submission_round = Report.SubmissionRound.REVIEW
    report.is_locked = False
    sync_group_report_teacher(report)
    report.save()
    _mark_late_resubmit(report)
    log_activity(request.user, ActivityLog.Action.RESUBMITTED, report)
    if report.group_id:
        notify_group_submission_stakeholders(report, submitter=request.user, is_resubmit=True)
    else:
        notify_report_stakeholders_sync(
            report,
            f'New version uploaded for "{report.title}".',
            link=f'/reports/{report.pk}/',
        )
        notify_teacher_for_report_submission(report, submitter=request.user, is_resubmit=True)
    queue_report_submitted_email(report.pk)
    messages.success(request, f'New version uploaded (archived as v{next_num}).')
    return redirect('reports:detail', pk=pk)


@login_required
@require_POST
def add_comment(request, pk):
    report = get_object_or_404(Report, pk=pk)
    if not _can_view_report(request.user, report):
        raise Http404()
    if report.is_locked and request.user.role == User.Role.STUDENT:
        messages.error(request, 'This report is locked.')
        return redirect('reports:detail', pk=pk)
    if request.user.role == User.Role.STUDENT and not _student_can_act_on_report(request.user, report):
        raise Http404()

    form = CommentForm(request.POST)
    if form.is_valid():
        c = form.save(commit=False)
        c.report = report
        c.user = request.user
        c.save()
        log_activity(request.user, ActivityLog.Action.COMMENT, report)
        target = report.student
        if request.user == report.student:
            report_teacher = get_report_assigned_teacher(report)
            if report_teacher:
                create_in_app_notification(report_teacher, f'New comment on "{report.title}"', link=f'/reports/{report.pk}/')
        else:
            notify_report_stakeholders_sync(
                report,
                f'Your teacher commented on "{report.title}". Open the report to read the feedback.',
                link=f'/reports/{report.pk}/',
            )
        messages.success(request, 'Comment posted.')
    else:
        messages.error(request, 'Could not save comment.')
    return redirect('reports:detail', pk=pk)


@login_required
@require_POST
def delete_report(request, pk):
    report = get_object_or_404(Report, pk=pk)
    current_user = request.user
    if current_user.role == User.Role.STUDENT:
        if report.student_id != current_user.id or report.status == Report.Status.APPROVED:
            messages.error(request, 'You cannot delete this report.')
            return redirect('reports:my_reports')
    elif current_user.role not in (User.Role.TEACHER, User.Role.ADMIN):
        raise Http404()

    report.is_deleted = True
    report.save(update_fields=['is_deleted'])
    log_activity(current_user, ActivityLog.Action.DELETED, report)
    messages.success(request, 'Report moved to trash (soft delete).')
    if current_user.role == User.Role.STUDENT:
        return redirect('reports:my_reports')
    return redirect('reports:list')


@login_required
@role_required(User.Role.ADMIN)
@require_POST
def restore_report(request, pk):
    report = get_object_or_404(Report, pk=pk)
    report.is_deleted = False
    report.save(update_fields=['is_deleted'])
    log_activity(request.user, ActivityLog.Action.RESTORED, report)
    messages.success(request, 'Report restored.')
    return redirect('reports:detail', pk=pk)


@login_required
@role_required(User.Role.ADMIN)
@require_POST
def bulk_reports_action(request):
    ids = request.POST.get('ids', '')
    action = request.POST.get('bulk_action', '')
    id_list = [int(x) for x in ids.split(',') if x.strip().isdigit()]
    if not id_list or action not in ('approve', 'reject'):
        messages.error(request, 'Invalid bulk action.')
        return redirect('reports:list')

    qs = Report.objects.filter(
        pk__in=id_list,
        teacher_approved=True,
        status=Report.Status.PENDING,
        admin_approved=False,
        is_deleted=False,
    )
    if action == 'approve':
        for r in list(qs):
            if r.marks is None:
                r.marks = r.teacher_marks or 0
            r.admin_approved = True
            r.refresh_status_from_flags()
            r.save()
            log_activity(request.user, ActivityLog.Action.ADMIN_APPROVED, r)
            notify_report_stakeholders_sync(
                r,
                f'Bulk approval: "{r.title}" approved.',
                link=f'/reports/{r.pk}/',
            )
            notify_admin_final_approval(r)
        messages.success(request, f'Approved {qs.count()} report(s).')
    else:
        reason = request.POST.get('bulk_reason', 'Bulk rejection')
        for r in Report.objects.filter(pk__in=id_list):
            r.admin_approved = False
            r.teacher_approved = False
            r.status = Report.Status.REJECTED
            r.rejection_reason = reason
            r.is_locked = False
            r.save()
            log_activity(request.user, ActivityLog.Action.ADMIN_REJECTED, r, detail=reason[:500])
        messages.warning(request, 'Selected reports rejected.')
    return redirect('reports:list')


@login_required
@role_required(User.Role.ADMIN)
def export_reports_csv(request):
    qs = Report.objects.select_related('student').filter(is_deleted=False).order_by('-submitted_at')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="reports_export.csv"'
    w = csv.writer(response)
    w.writerow(
        ['ID', 'Title', 'Student', 'Department', 'Status', 'Marks', 'Late', 'Submitted', 'Teacher OK', 'Admin OK']
    )
    for r in qs:
        w.writerow(
            [
                r.pk,
                r.title,
                r.student.username,
                getattr(r.student, 'department', '') or '',
                r.status,
                r.marks if r.marks is not None else '',
                'Y' if r.is_late_submission else 'N',
                r.submitted_at.isoformat(),
                'Y' if r.teacher_approved else 'N',
                'Y' if r.admin_approved else 'N',
            ]
        )
    return response


@login_required
def notification_list(request):
    qs = Notification.objects.filter(user=request.user)
    from apps.dashboard.list_helpers import apply_sort, paginate_table, get_filter_querystring

    qs = apply_sort(
        qs,
        request,
        allowed={'created_at': 'created_at', 'message': 'message'},
        default_field='created_at',
        default_dir='desc',
    )
    page, filter_querystring = paginate_table(request, qs)
    return render(
        request,
        'reports/notifications.html',
        {
            'page_obj': page,
            'filter_querystring': filter_querystring,
        },
    )


@login_required
def notification_open(request, pk):
    """Mark notification read and go to its linked page (GET — works from bell menu and list)."""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=['is_read'])
    target_link = (notification.link or '').strip()
    if target_link:
        return redirect(target_link)
    return redirect('reports:notifications')


@login_required
@require_POST
def notification_mark_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save(update_fields=['is_read'])
    if notification.link:
        return redirect(notification.link)
    return redirect('reports:notifications')


@login_required
@require_POST
def notifications_mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, 'All notifications marked read.')
    return redirect('reports:notifications')


@login_required
@require_POST
def toggle_bookmark(request, pk):
    report = get_object_or_404(Report, pk=pk)
    if not _can_view_report(request.user, report):
        raise Http404()
    obj, created = ReportBookmark.objects.get_or_create(user=request.user, report=report)
    if not created:
        obj.delete()
        messages.info(request, 'Removed from bookmarks.')
    else:
        messages.success(request, 'Bookmarked.')
    return redirect('reports:detail', pk=pk)


@login_required
@role_required(User.Role.STUDENT)
@require_POST
def request_reevaluation(request, pk):
    report = get_object_or_404(Report, pk=pk, student=request.user)
    if report.status != Report.Status.APPROVED:
        messages.error(request, 'Re-evaluation applies to approved reports only.')
        return redirect('reports:detail', pk=pk)
    if ReEvaluationRequest.objects.filter(
        report=report, status=ReEvaluationRequest.Status.PENDING
    ).exists():
        messages.warning(request, 'A re-evaluation request is already pending.')
        return redirect('reports:detail', pk=pk)
    form = ReEvaluationRequestForm(request.POST)
    if form.is_valid():
        ReEvaluationRequest.objects.create(
            report=report,
            student=request.user,
            reason=form.cleaned_data['reason'],
        )
        log_activity(request.user, ActivityLog.Action.REEVAL_REQUESTED, report)
        for admin_user in User.objects.filter(role=User.Role.ADMIN):
            create_in_app_notification(admin_user, f'Re-evaluation requested for "{report.title}"', link=f'/reports/{report.pk}/')
        messages.success(request, 'Request submitted.')
    return redirect('reports:detail', pk=pk)


@login_required
@role_required(User.Role.ADMIN)
@require_POST
def resolve_reevaluation(request, reeval_pk):
    reevaluation_request = get_object_or_404(
        ReEvaluationRequest, pk=reeval_pk, status=ReEvaluationRequest.Status.PENDING
    )
    action = request.POST.get('resolve_action', '')
    new_marks = request.POST.get('updated_marks')
    if action == 'approve' and new_marks and new_marks.isdigit():
        reevaluation_request.status = ReEvaluationRequest.Status.APPROVED
        reevaluation_request.updated_marks = int(new_marks)
        reevaluation_request.resolved_at = timezone.now()
        reevaluation_request.save()
        report = reevaluation_request.report
        report.marks = reevaluation_request.updated_marks
        report.save(update_fields=['marks'])
        log_activity(
            request.user,
            ActivityLog.Action.REEVAL_RESOLVED,
            report,
            detail=f'Marks updated to {report.marks}',
        )
        create_in_app_notification(
            reevaluation_request.student,
            f'Re-evaluation approved. Updated marks: {report.marks}',
            link=f'/reports/{report.pk}/',
        )
        messages.success(request, 'Re-evaluation resolved.')
    elif action == 'reject':
        reevaluation_request.status = ReEvaluationRequest.Status.REJECTED
        reevaluation_request.resolved_at = timezone.now()
        reevaluation_request.save()
        create_in_app_notification(
            reevaluation_request.student,
            'Your re-evaluation request was declined.',
            link=f'/reports/{reevaluation_request.report.pk}/',
        )
        messages.info(request, 'Request rejected.')
    return redirect('reports:detail', pk=reevaluation_request.report_id)


def public_student_profile(request, username):
    student = get_object_or_404(
        User.objects.select_related('assigned_teacher'),
        username=username,
        role=User.Role.STUDENT,
    )
    staff_view = _can_view_student_full_profile(request.user, student)
    base_qs = (
        Report.objects.filter(is_deleted=False)
        .filter(_student_report_membership_q(student))
        .select_related('group', 'rubric')
        .distinct()
    )

    if staff_view:
        reports = base_qs.order_by('-submitted_at')
    else:
        reports = base_qs.filter(status=Report.Status.APPROVED).order_by('-submitted_at')

    stats = {
        'total': base_qs.count(),
        'approved': base_qs.filter(status=Report.Status.APPROVED).count(),
        'pending': base_qs.filter(status=Report.Status.PENDING).count(),
        'rejected': base_qs.filter(status=Report.Status.REJECTED).count(),
        'certificates': base_qs.filter(
            status=Report.Status.APPROVED,
            certificate_generated=True,
        ).count(),
        'late': base_qs.filter(is_late_submission=True).count(),
    }
    marks_agg = base_qs.filter(marks__isnull=False).aggregate(avg_marks=Avg('marks'))
    stats['avg_marks'] = marks_agg['avg_marks']

    context = {
        'student': student,
        'reports': reports,
        'stats': stats,
        'staff_view': staff_view,
        'back_url': _safe_back_url(request) or _default_student_profile_back_url(request),
        'back_label': 'Back',
    }

    if request.user.is_authenticated:
        return render(request, 'reports/student_profile_app.html', context)
    return render(request, 'reports/student_profile_public.html', context)


@login_required
def download_certificate(request, pk):
    from application.services.certificate_service import CertificateService

    report = get_object_or_404(Report, pk=pk)
    if not _can_view_report(request.user, report):
        raise Http404()
    try:
        pdf_bytes = CertificateService().get_certificate_for_user(request.user, pk)
    except Exception:
        messages.error(
            request,
            'Certificate is not available yet. The teacher must mark this as the final submission, '
            'and the report must be approved by both teacher and admin.',
        )
        return redirect('reports:detail', pk=pk)
    safe_name = (request.user.get_full_name() or request.user.username or 'student').replace(' ', '_')
    return FileResponse(
        io.BytesIO(pdf_bytes),
        as_attachment=True,
        filename=f'{safe_name}_project_certificate.pdf',
        content_type='application/pdf',
    )


@login_required
@role_required(User.Role.ADMIN)
@require_POST
def certificate_template_analyze(request):
    """Extract design from uploaded reference image (admin designer step 1)."""
    from application.services.certificate_template_service import CertificateTemplateService
    from infrastructure.pdf.certificate_template_analyzer import CertificateImageAnalysisError

    uploaded = request.FILES.get('reference_image')
    if not uploaded:
        return JsonResponse(
            {'success': False, 'message': 'Choose a clear certificate image first (PNG, JPG, or WEBP).'},
            status=400,
        )
    service = CertificateTemplateService()
    try:
        analysis = service.analyze_upload(uploaded)
    except CertificateImageAnalysisError as exc:
        return JsonResponse({'success': False, 'message': exc.message}, status=400)
    except Exception:
        return JsonResponse(
            {
                'success': False,
                'message': 'Could not read that image. Upload a sharper PNG, JPG, or WEBP certificate.',
            },
            status=400,
        )
    return JsonResponse(
        {
            'success': True,
            'message': 'Template generated from your reference image. Review the tabs, edit anything, then save or preview.',
            'data': analysis,
        }
    )


@login_required
@role_required(User.Role.ADMIN)
@require_POST
def certificate_template_preview_draft(request):
    """Preview certificate PDF from current form without saving."""
    from application.services.certificate_template_service import CertificateTemplateService
    from apps.reports.forms import CertificateTemplateForm
    from core.exceptions import PermissionAppError, ValidationAppError

    template_pk = request.POST.get('template_pk')
    instance = None
    if template_pk:
        instance = CertificateTemplate.objects.filter(pk=template_pk).first()
    elif request.POST.get('create_new_template') == '1':
        instance = CertificateTemplate(is_active=False, name='Draft certificate template')

    form = CertificateTemplateForm(request.POST, request.FILES, instance=instance)
    service = CertificateTemplateService()
    try:
        pdf_bytes = service.preview_from_form(request.user, form)
    except ValidationAppError as exc:
        return JsonResponse({'success': False, 'message': exc.message}, status=400)
    except PermissionAppError as exc:
        return JsonResponse({'success': False, 'message': exc.message}, status=403)
    except Exception:
        return JsonResponse(
            {
                'success': False,
                'message': 'Could not preview this template. Check your reference image and try again.',
            },
            status=400,
        )
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="certificate-preview-draft.pdf"'
    return response


@login_required
@role_required(User.Role.ADMIN)
def certificate_template_preview(request):
    from application.services.certificate_template_service import CertificateTemplateService
    from core.exceptions import PermissionAppError

    try:
        pdf_bytes = CertificateTemplateService().build_preview_pdf(request.user)
    except PermissionAppError as exc:
        messages.error(request, friendly_message(exc))
        return redirect('dashboard:admin_dashboard')
    except Exception:
        messages.error(
            request,
            'Could not generate certificate preview. Re-upload the reference image in Customize template.',
        )
        return redirect('dashboard:admin_dashboard')
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="certificate-preview.pdf"'
    return response


@login_required
@role_required(User.Role.ADMIN)
@require_POST
def assign_report_teacher(request, pk):
    report = get_object_or_404(Report, pk=pk)
    teacher_id = request.POST.get('teacher_id', '').strip()
    from application.services.report_service import ReportService
    from core.exceptions import ValidationAppError

    service = ReportService()
    try:
        service.assign_report_teacher(
            request.user,
            pk,
            int(teacher_id) if teacher_id else None,
        )
    except ValidationAppError as exc:
        messages.error(request, friendly_message(exc))
    else:
        if report.group_id:
            messages.success(request, 'Group project teacher updated. All group members were notified.')
        else:
            messages.success(request, 'Project teacher updated for this report.')
    return redirect('reports:detail', pk=pk)
