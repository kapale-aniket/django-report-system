"""Async email delivery."""
from celery import shared_task

from tasks.celery_tasks.email_tasks import (
    send_admin_final_approval_email_task,
    send_certificate_email_task,
    send_rejection_email_task,
    send_report_submitted_email_task,
    send_teacher_approved_email_task,
    send_teacher_final_approval_email_task,
)
from tasks.celery_tasks.notification_tasks import notify_user_task

__all__ = [
    'send_admin_final_approval_email_task',
    'send_certificate_email_task',
    'send_rejection_email_task',
    'send_report_submitted_email_task',
    'send_teacher_approved_email_task',
    'send_teacher_final_approval_email_task',
    'notify_user_task',
]
