"""Dispatch helpers — queue Celery tasks or run synchronously in dev."""
from django.conf import settings


def _use_celery() -> bool:
    return getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False) is False


def _queue_or_run(task, *args):
    if _use_celery():
        task.delay(*args)
    else:
        task(*args)


def queue_rejection_email(report_id: int, reason: str) -> None:
    from tasks.celery_tasks.email_tasks import send_rejection_email_task

    _queue_or_run(send_rejection_email_task, report_id, reason)


def queue_certificate_email(report_id: int) -> None:
    from tasks.celery_tasks.email_tasks import send_certificate_email_task

    _queue_or_run(send_certificate_email_task, report_id)


def queue_report_submitted_email(report_id: int) -> None:
    from tasks.celery_tasks.email_tasks import send_report_submitted_email_task

    _queue_or_run(send_report_submitted_email_task, report_id)


def queue_teacher_approved_email(report_id: int) -> None:
    from tasks.celery_tasks.email_tasks import send_teacher_approved_email_task

    _queue_or_run(send_teacher_approved_email_task, report_id)


def queue_admin_final_approval_email(report_id: int) -> None:
    from tasks.celery_tasks.email_tasks import send_admin_final_approval_email_task

    _queue_or_run(send_admin_final_approval_email_task, report_id)


def queue_teacher_final_approval_email(report_id: int) -> None:
    from tasks.celery_tasks.email_tasks import send_teacher_final_approval_email_task

    _queue_or_run(send_teacher_final_approval_email_task, report_id)


def queue_notify_user(user_id: int, message: str, link: str = '') -> None:
    from tasks.celery_tasks.notification_tasks import notify_user_task

    _queue_or_run(notify_user_task, user_id, message, link)


def queue_report_ai_analysis(report_id: int) -> None:
    from django.conf import settings

    if not getattr(settings, 'AI_FEATURES_ENABLED', True):
        return

    from tasks.celery_tasks.ai_tasks import process_report_ai_task

    _queue_or_run(process_report_ai_task, report_id)
