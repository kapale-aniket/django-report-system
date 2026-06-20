"""Prevent browsers from caching authenticated app pages (back-button after logout)."""

PRIVATE_PREFIXES = (
    '/accounts/redirect/',
    '/accounts/users/',
    '/accounts/pending-students/',
    '/accounts/session-check/',
    '/reports/',
    '/messages/',
    '/qa/',
    '/admin-dashboard/',
    '/teacher-dashboard/',
    '/student-dashboard/',
)


def _apply_no_cache_headers(response) -> None:
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0, private'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    response['Vary'] = 'Cookie'


class NoCacheAuthenticatedMiddleware:
    """Mark private responses so the back button cannot show stale logged-in pages."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if getattr(request, 'user', None) and request.user.is_authenticated:
            _apply_no_cache_headers(response)
            return response
        if request.path.startswith(PRIVATE_PREFIXES):
            _apply_no_cache_headers(response)
        return response
