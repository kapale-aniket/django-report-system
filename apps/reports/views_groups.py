"""Project group list, creation, and admin teacher assignment views."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.decorators import role_required
from apps.accounts.infrastructure.models import User

from .forms import ProjectGroupAssignTeacherForm, ProjectGroupCreateForm
from .group_helpers import get_department_students
from .settings_helpers import get_group_project_rules
from application.services.project_group_service import ProjectGroupService


@login_required
@role_required(User.Role.STUDENT)
def project_groups_list(request):
    service = ProjectGroupService()
    return render(
        request,
        'reports/project_groups.html',
        {
            'my_groups': service.list_my_groups(request.user),
            'public_groups': service.list_public_groups(request.user),
        },
    )


@login_required
@role_required(User.Role.STUDENT)
def project_group_create(request):
    if request.method == 'POST':
        form = ProjectGroupCreateForm(request.POST, user=request.user)
        if form.is_valid():
            service = ProjectGroupService()
            group = service.create_group(
                request.user,
                {
                    'name': form.cleaned_data['name'],
                    'description': form.cleaned_data.get('description', ''),
                    'project_mate_ids_list': form.cleaned_data['project_mate_ids_list'],
                },
            )
            messages.success(request, f'Project group "{group.name}" created and published.')
            return redirect('reports:project_groups')
    else:
        form = ProjectGroupCreateForm(user=request.user)

    return render(
        request,
        'reports/project_group_create.html',
        {
            'form': form,
            'department_students': get_department_students(request.user),
            'group_rules': get_group_project_rules(),
        },
    )


@login_required
@role_required(User.Role.ADMIN)
def project_groups_admin(request):
    from apps.reports.group_helpers import get_teachers_for_department

    service = ProjectGroupService()
    department = (request.GET.get('department') or '').strip()
    groups = service.list_groups_for_admin(request.user, department=department)
    rows = [
        {
            'group': group,
            'teachers': list(get_teachers_for_department(group.department)),
        }
        for group in groups
    ]
    return render(
        request,
        'reports/project_groups_admin.html',
        {
            'rows': rows,
            'department_filter': department,
        },
    )


@login_required
@role_required(User.Role.ADMIN)
@require_POST
def project_group_assign_teacher(request, pk):
    service = ProjectGroupService()
    group = service.get_group(request.user, pk)
    form = ProjectGroupAssignTeacherForm(request.POST, group=group)
    if form.is_valid():
        service.assign_teacher(request.user, pk, form.cleaned_data.get('teacher_id'))
        messages.success(request, f'Teacher updated for group "{group.name}".')
    else:
        messages.error(request, 'Could not assign teacher. Check your selection.')
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
    if next_url and next_url.startswith('/') and not next_url.startswith('//'):
        return redirect(next_url)
    return redirect('reports:project_groups_admin')
