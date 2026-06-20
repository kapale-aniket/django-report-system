"""Helpers for report discussion threads."""
from apps.accounts.infrastructure.models import User
from apps.reports.infrastructure.models import Comment


def post_report_comment(report, user, message: str) -> Comment | None:
    """Save a visible comment on the report thread."""
    text = (message or '').strip()
    if not text:
        return None
    return Comment.objects.create(report=report, user=user, message=text)


def staff_comments_for_report(report):
    """Comments left by teachers or admins, oldest first."""
    return (
        report.comments.filter(user__role__in=(User.Role.TEACHER, User.Role.ADMIN))
        .select_related('user')
        .order_by('created_at')
    )
