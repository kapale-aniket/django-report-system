"""Resolve submission rules for individual vs group projects."""
from __future__ import annotations

from apps.reports.infrastructure.models import Report, SystemSettings


def get_group_project_rules(settings_obj=None) -> dict:
    settings_obj = settings_obj or SystemSettings.get_settings()
    return {
        'submission_deadline': settings_obj.group_submission_deadline or settings_obj.submission_deadline,
        'max_attempts': settings_obj.group_max_attempts,
        'min_members': settings_obj.group_min_members,
        'max_members': settings_obj.group_max_members,
    }


def get_individual_project_rules(settings_obj=None) -> dict:
    settings_obj = settings_obj or SystemSettings.get_settings()
    return {
        'submission_deadline': settings_obj.submission_deadline,
        'max_attempts': settings_obj.max_attempts,
    }


def get_report_submission_rules(report, settings_obj=None) -> dict:
    if report is not None and report.group_id:
        return get_group_project_rules(settings_obj)
    return get_individual_project_rules(settings_obj)


def get_max_attempts_for_report(report, settings_obj=None) -> int:
    return get_report_submission_rules(report, settings_obj)['max_attempts']


def get_submission_deadline_for_report(report, settings_obj=None):
    return get_report_submission_rules(report, settings_obj)['submission_deadline']


def is_group_report(report) -> bool:
    return report is not None and bool(report.group_id)
