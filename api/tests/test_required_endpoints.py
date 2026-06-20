"""Verify all frontend-required /api/v1/ routes are registered."""
from django.test import SimpleTestCase
from django.urls import resolve, reverse


REQUIRED_API_ROUTES = [
    ('accounts_api:login', {}, 'POST'),
    ('accounts_api:logout', {}, 'POST'),
    ('accounts_api:profile', {}, 'GET'),
    ('accounts_api:profile', {}, 'PATCH'),
    ('accounts_api:profile_photo', {}, 'POST'),
    ('accounts_api:change_password', {}, 'POST'),
    ('accounts_api:departments', {}, 'GET'),
    ('accounts_api:departments', {}, 'POST'),
    ('accounts_api:teachers_by_department', {}, 'GET'),
    ('accounts_api:user_create', {}, 'POST'),
    ('accounts_api:user_approve', {'pk': 1}, 'POST'),
    ('accounts_api:user_set_active', {'pk': 1}, 'POST'),
    ('accounts_api:user_delete', {'pk': 1}, 'DELETE'),
    ('accounts_api:user_update', {'pk': 1}, 'PATCH'),
    ('accounts_api:assign_teacher', {'pk': 1}, 'POST'),
    ('accounts_api:teacher_students', {'pk': 1}, 'GET'),
    ('reports_api:report_list', {}, 'GET'),
    ('reports_api:submit', {}, 'POST'),
    ('reports_api:bulk_action', {}, 'POST'),
    ('reports_api:settings', {}, 'PUT'),
    ('reports_api:restore', {'pk': 1}, 'POST'),
    ('reports_api:toggle_pin', {'pk': 1}, 'POST'),
    ('reports_api:bookmark', {'pk': 1}, 'POST'),
    ('reports_api:teacher_approve', {'pk': 1}, 'POST'),
    ('reports_api:admin_approve', {'pk': 1}, 'POST'),
    ('reports_api:resubmit', {'pk': 1}, 'POST'),
    ('reports_api:reeval_request', {'pk': 1}, 'POST'),
    ('reports_api:extension_request', {'pk': 1}, 'POST'),
    ('reports_api:comment', {'pk': 1}, 'POST'),
    ('reports_api:teacher_reject', {'pk': 1}, 'POST'),
    ('reports_api:admin_reject', {'pk': 1}, 'POST'),
    ('reports_api:delete', {'pk': 1}, 'POST'),
    ('reports_api:ai_suggestions', {'pk': 1}, 'GET'),
    ('reports_api:ai_process', {'pk': 1}, 'POST'),
    ('reports_api:notifications_mark_all_read', {}, 'POST'),
    ('reports_api:extension_resolve', {'pk': 1}, 'POST'),
    ('reports_api:reeval_resolve', {'reeval_pk': 1}, 'POST'),
    ('qa_api:ask', {}, 'POST'),
    ('qa_api:visitor_ask', {}, 'POST'),
    ('qa_api:reply', {'question_id': 1}, 'POST'),
    ('qa_api:visitor_reply', {'question_id': 1}, 'POST'),
    ('qa_api:suggest_reply', {}, 'POST'),
    ('messaging_api:compose', {}, 'POST'),
    ('messaging_api:mark_read', {'message_id': 1}, 'POST'),
    ('certificates_api:verify', {}, 'GET'),
    ('dashboard_api:admin_analytics', {}, 'GET'),
    ('dashboard_api:teacher_dashboard', {}, 'GET'),
    ('dashboard_api:student_dashboard', {}, 'GET'),
]


class RequiredAPIRoutesTest(SimpleTestCase):
    def test_required_routes_resolve(self):
        missing = []
        for name, kwargs, _method in REQUIRED_API_ROUTES:
            try:
                path = reverse(name, kwargs=kwargs)
                resolve(path)
            except Exception as exc:  # noqa: BLE001 — collect all missing routes
                missing.append(f'{name} {kwargs}: {exc}')
        self.assertEqual(missing, [], 'Missing API routes:\n' + '\n'.join(missing))
