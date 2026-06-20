from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_GET, require_POST

from .department_choices import get_department_choices
from .decorators import role_required
from .forms import (
    AdminCreateUserForm,
    RoleLoginForm,
    StudentRegistrationForm,
    TeacherRegistrationForm,
    UserFilterForm,
)
from .models import User


class AppLoginView(LoginView):
    """Single sign-in page — username and password only; role comes from the account."""
    form_class = RoleLoginForm
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('accounts:post_login_redirect')


@login_required
def post_login_redirect(request):
    """Route authenticated users to their role dashboard."""
    role = request.user.role
    if role == User.Role.ADMIN:
        return redirect('dashboard:admin_dashboard')
    if role == User.Role.TEACHER:
        return redirect('dashboard:teacher_dashboard')
    if role == User.Role.STUDENT:
        return redirect('dashboard:student_dashboard')
    return redirect('accounts:login')


def register_hub(request):
    """Pick Student or Teacher self-registration."""
    if request.user.is_authenticated:
        return redirect('accounts:post_login_redirect')
    return render(request, 'accounts/register_select.html')


def logout_view(request):
    logout(request)
    response = render(request, 'accounts/logout_redirect.html')
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0, private'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


@require_GET
def session_check(request):
    """Lightweight session probe for client-side auth guard (back/forward cache)."""
    if request.user.is_authenticated:
        response = JsonResponse({'authenticated': True})
    else:
        response = JsonResponse({'authenticated': False}, status=401)
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0, private'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


def register_student(request):
    if request.user.is_authenticated:
        return redirect('accounts:post_login_redirect')
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                'Registration received. You cannot sign in until an administrator or your assigned teacher '
                'approves your account. Contact your department if you need a teacher assigned first.',
            )
            return redirect('dashboard:landing')
    else:
        form = StudentRegistrationForm()
    return render(request, 'accounts/register_student.html', {'form': form})


def register_teacher(request):
    if request.user.is_authenticated:
        return redirect('accounts:post_login_redirect')
    if request.method == 'POST':
        form = TeacherRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                'Registration received. You cannot sign in until an administrator approves your account.',
            )
            return redirect('dashboard:landing')
    else:
        form = TeacherRegistrationForm()
    return render(request, 'accounts/register_teacher.html', {'form': form})


@login_required
@role_required(User.Role.ADMIN)
@require_POST
def approve_user(request, pk):
    target_user = get_object_or_404(User, pk=pk)
    if target_user.is_superuser or target_user == request.user:
        messages.error(request, 'Cannot modify this account.')
        return redirect('accounts:user_management')
    if target_user.role == User.Role.ADMIN:
        messages.error(request, 'Use superuser tools for admin accounts.')
        return redirect('accounts:user_management')
    target_user.is_active = True
    target_user.save(update_fields=['is_active'])
    messages.success(request, f'Approved: {target_user.username} can now sign in.')
    return redirect('accounts:user_management')


@login_required
@role_required(User.Role.TEACHER)
@require_POST
def approve_student(request, pk):
    student = get_object_or_404(User, pk=pk, role=User.Role.STUDENT)
    if student.assigned_teacher_id != request.user.id:
        messages.error(request, 'You can only approve students assigned to you.')
        return redirect('accounts:pending_students')
    student.is_active = True
    student.save(update_fields=['is_active'])
    messages.success(request, f'Student {student.username} can now sign in.')
    return redirect('accounts:pending_students')


@login_required
@role_required(User.Role.TEACHER)
def pending_students(request):
    qs = User.objects.filter(
        role=User.Role.STUDENT,
        assigned_teacher=request.user,
        is_active=False,
    )
    q = request.GET.get('search', '').strip()
    if q:
        qs = qs.filter(
            Q(username__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(email__icontains=q)
        )
    from apps.dashboard.list_helpers import apply_sort, paginate_table, get_filter_querystring

    qs = apply_sort(
        qs,
        request,
        allowed={'username': 'username', 'email': 'email', 'department': 'department'},
        default_field='username',
        default_dir='asc',
    )
    page, _ = paginate_table(request, qs)
    return render(
        request,
        'accounts/pending_students.html',
        {
            'page_obj': page,
            'filter_querystring': get_filter_querystring(request),
            'sort_by': request.GET.get('sort_by', 'username'),
            'sort_dir': request.GET.get('sort_dir', 'asc'),
            'sort_options': [
                ('username', 'Username'),
                ('email', 'Email'),
                ('department', 'Department'),
            ],
        },
    )


@role_required(User.Role.ADMIN)
def user_list_create(request):
    filter_form = UserFilterForm(request.GET or None)
    users = User.objects.exclude(role=User.Role.ADMIN)

    role = (request.GET.get('role') or '').strip()
    status = (request.GET.get('status') or '').strip()
    search = (request.GET.get('search') or '').strip()
    if filter_form.is_valid():
        role = filter_form.cleaned_data.get('role') or role
        status = filter_form.cleaned_data.get('status') or status
        search = (filter_form.cleaned_data.get('search') or '').strip() or search
    if role:
        users = users.filter(role=role)
    if status == 'pending':
        users = users.filter(is_active=False)
    elif status == 'active':
        users = users.filter(is_active=True)
    if search:
        users = users.filter(
            Q(username__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
        )

    from apps.dashboard.list_helpers import apply_sort, paginate_table

    sort_by = request.GET.get('sort_by', 'username')
    sort_dir = request.GET.get('sort_dir', 'asc')
    users = users.select_related('assigned_teacher').annotate(
        assigned_student_count=Count('assigned_students', filter=Q(assigned_students__role=User.Role.STUDENT))
    )
    users = apply_sort(
        users,
        request,
        allowed={
            'username': 'username',
            'role': 'role',
            'department': 'department',
            'email': 'email',
        },
        default_field='username',
        default_dir='asc',
    )
    page, filter_querystring = paginate_table(request, users)

    if request.method == 'POST':
        form = AdminCreateUserForm(request.POST)
        if form.is_valid():
            from application.services.user_management_service import UserManagementService
            from core.exceptions import ValidationAppError

            cleaned = form.cleaned_data
            teacher = cleaned.get('assigned_teacher')
            service = UserManagementService()
            try:
                result = service.create_user(
                    {
                        'first_name': cleaned.get('first_name', ''),
                        'last_name': cleaned.get('last_name', ''),
                        'email': cleaned['email'],
                        'role': cleaned['role'],
                        'department': cleaned.get('department', ''),
                        'assigned_teacher_id': teacher.pk if teacher else None,
                    }
                )
            except ValidationAppError as exc:
                messages.error(request, str(exc))
            else:
                profile = result.profile
                if result.email_sent:
                    messages.success(
                        request,
                        f'User "{profile.username}" was created. Login details were emailed to {profile.email}.',
                    )
                else:
                    messages.warning(
                        request,
                        f'User "{profile.username}" was created, but the welcome email could not be delivered. '
                        f'{result.email_notice} '
                        f'Username: {profile.username} · Password: {result.password}',
                    )
                return redirect('accounts:user_management')
    else:
        form = AdminCreateUserForm()

    pending_count = User.objects.filter(is_active=False).exclude(role=User.Role.ADMIN).count()
    teachers = User.objects.filter(role=User.Role.TEACHER, is_active=True).order_by('username')
    return render(
        request,
        'accounts/user_management.html',
        {
            'page_obj': page,
            'form': form,
            'filter_form': filter_form,
            'teachers': teachers,
            'pending_count': pending_count,
            'filter_querystring': filter_querystring,
            'sort_by': sort_by,
            'sort_dir': sort_dir,
            'sort_options': [
                ('username', 'Username'),
                ('role', 'Role'),
                ('department', 'Department'),
                ('email', 'Email'),
            ],
            'department_choices': get_department_choices(include_add_option=True),
        },
    )


@login_required
@role_required(User.Role.ADMIN)
@require_POST
def user_set_active(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user.is_superuser or user == request.user or user.role == User.Role.ADMIN:
        messages.error(request, 'Cannot modify this account.')
        return redirect('accounts:user_management')
    raw = request.POST.get('is_active', '')
    is_active = raw in ('1', 'true', 'True', 'on')
    user.is_active = is_active
    user.save(update_fields=['is_active'])
    state = 'activated' if is_active else 'deactivated'
    messages.success(request, f'User "{user.username}" {state}.')
    return redirect('accounts:user_management')


@login_required
@role_required(User.Role.ADMIN)
@require_POST
def user_update(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user.is_superuser or user == request.user or user.role == User.Role.ADMIN:
        messages.error(request, 'Cannot modify this account.')
        return redirect('accounts:user_management')
    user.first_name = request.POST.get('first_name', user.first_name).strip()
    user.last_name = request.POST.get('last_name', user.last_name).strip()
    user.email = request.POST.get('email', user.email).strip()
    user.department = request.POST.get('department', user.department).strip()
    user.save(update_fields=['first_name', 'last_name', 'email', 'department'])
    messages.success(request, f'Updated profile for "{user.username}".')
    return redirect('accounts:user_management')


@role_required(User.Role.ADMIN)
def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user.role == User.Role.ADMIN or user == request.user:
        messages.error(request, 'Cannot delete this user.')
        return redirect('accounts:user_management')
    username = user.username
    user.delete()
    messages.success(request, f'User "{username}" deleted.')
    return redirect('accounts:user_management')


@login_required
@role_required(User.Role.ADMIN)
@require_POST
def assign_teacher(request, pk):
    student = get_object_or_404(User, pk=pk, role=User.Role.STUDENT)
    teacher_id = request.POST.get('teacher_id')
    if teacher_id in ('', None):
        student.assigned_teacher = None
    else:
        teacher = get_object_or_404(User, pk=int(teacher_id), role=User.Role.TEACHER)
        student.assigned_teacher = teacher
    student.save(update_fields=['assigned_teacher'])
    messages.success(request, f'Updated teacher for {student.username}.')
    return redirect('accounts:user_management')
