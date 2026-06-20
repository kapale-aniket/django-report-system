"""Detect active sidebar section from URL (no per-view boilerplate)."""


def app_navigation(request):
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {}
    path = request.path.rstrip('/') or '/'

    if '/accounts/pending-students' in path:
        section = 'pending'
    elif '/accounts/users' in path:
        section = 'users'
    elif '/messages' in path:
        section = 'messages'
    elif '/reports/activity-log' in path:
        section = 'audit'
    elif '/reports/leaderboard' in path:
        section = 'leaderboard'
    elif '/reports/submission-tracking' in path:
        section = 'tracking'
    elif '/reports/teacher-workload' in path:
        section = 'workload'
    elif '/reports/extensions' in path:
        section = 'extensions'
    elif path.startswith('/qa'):
        section = 'qa'
    elif '/reports/groups' in path:
        section = 'project_groups'
    elif '/reports/submit' in path:
        section = 'submit'
    elif '/reports/my' in path:
        section = 'my_reports'
    elif '/reports/list' in path:
        section = 'reports'
    elif '/reports/notifications' in path:
        section = 'notifications'
    elif '/reports/export' in path:
        section = 'reports'
    elif path.startswith('/reports/') and path.rstrip('/').split('/')[-1].isdigit():
        section = 'my_reports' if getattr(request.user, 'role', None) == 'student' else 'reports'
    elif 'dashboard' in path:
        section = 'dashboard'
    else:
        section = 'dashboard'

    role = getattr(request.user, 'role', None)
    if role == 'admin':
        dash_url = 'dashboard:admin_dashboard'
    elif role == 'teacher':
        dash_url = 'dashboard:teacher_dashboard'
    else:
        dash_url = 'dashboard:student_dashboard'

    return {
        'app_nav_section': section,
        'app_dashboard_url': dash_url,
    }
