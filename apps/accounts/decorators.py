from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse


def role_required(*allowed_roles):
    """
    Restrict view to users whose role is in allowed_roles.
    allowed_roles: 'admin', 'teacher', 'student'
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            role = getattr(request.user, 'role', None)
            if role not in allowed_roles:
                return redirect('accounts:post_login_redirect')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator
