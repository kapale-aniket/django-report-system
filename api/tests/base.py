"""Shared fixtures and helpers for API integration tests."""
from __future__ import annotations

import shutil
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.infrastructure.models import Department
from apps.messaging.infrastructure.models import Message
from apps.qa.infrastructure.models import QAItem, UserQuestion, VisitorQuestion
from apps.reports.infrastructure.models import (
    DeadlineExtensionRequest,
    Notification,
    ProjectGroup,
    ReEvaluationRequest,
    Report,
    Rubric,
    SystemSettings,
)

User = get_user_model()

_fixtures_cache = None


def dummy_pdf(name: str = 'sample.pdf') -> SimpleUploadedFile:
    content = b'%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF'
    return SimpleUploadedFile(name, content, content_type='application/pdf')


def dummy_docx(name: str = 'sample.docx') -> SimpleUploadedFile:
    """Minimal DOCX (zip with word/document.xml) for upload validation tests."""
    import io
    import zipfile

    document_xml = (
        b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        b'<w:body><w:p><w:r><w:t>Sample project report text for testing.</w:t></w:r></w:p></w:body>'
        b'</w:document>'
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('word/document.xml', document_xml)
    return SimpleUploadedFile(
        name,
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    )


class APITestBase(APITestCase):
    """Creates admin, teacher, student, department, rubric, and system settings."""

    @classmethod
    def setUpTestData(cls):
        global _fixtures_cache
        if _fixtures_cache is None:
            _fixtures_cache = cls._build_fixtures()
        cls.password = _fixtures_cache['password']
        cls.department_name = _fixtures_cache['department_name']
        cls.department = _fixtures_cache['department']
        cls.admin = _fixtures_cache['admin']
        cls.teacher = _fixtures_cache['teacher']
        cls.student = _fixtures_cache['student']
        cls.pending_student = _fixtures_cache['pending_student']
        cls.rubric = _fixtures_cache['rubric']

    @classmethod
    def _build_fixtures(cls):
        password = 'TestPass1'
        department_name = 'Computer Science'
        department, _ = Department.objects.get_or_create(name=department_name)
        admin = User.objects.create_user(
            username='admin1',
            password=password,
            email='admin@test.com',
            role=User.Role.ADMIN,
            is_active=True,
            first_name='Ada',
            last_name='Min',
        )
        teacher = User.objects.create_user(
            username='teacher1',
            password=password,
            email='teacher@test.com',
            role=User.Role.TEACHER,
            department=department_name,
            is_active=True,
            first_name='Tea',
            last_name='Cher',
        )
        student = User.objects.create_user(
            username='student1',
            password=password,
            email='student@test.com',
            role=User.Role.STUDENT,
            department=department_name,
            is_active=True,
            assigned_teacher=teacher,
            first_name='Stu',
            last_name='Dent',
        )
        pending_student = User.objects.create_user(
            username='pending1',
            password=password,
            email='pending@test.com',
            role=User.Role.STUDENT,
            is_active=False,
        )
        SystemSettings.get_settings()
        rubric, _ = Rubric.objects.get_or_create(
            name='Default Rubric',
            defaults={
                'is_default': True,
                'is_active': True,
                'criteria_json': [
                    {'id': 1, 'name': 'Quality', 'max_score': 10, 'sort_order': 1},
                ],
            },
        )
        if not rubric.is_default:
            rubric.is_default = True
            rubric.is_active = True
            rubric.save(update_fields=['is_default', 'is_active'])
        return {
            'password': password,
            'department_name': department_name,
            'department': department,
            'admin': admin,
            'teacher': teacher,
            'student': student,
            'pending_student': pending_student,
            'rubric': rubric,
        }

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        global _fixtures_cache
        _fixtures_cache = None
        super().tearDownClass()
        media_root = Path(settings.MEDIA_ROOT)
        if media_root.exists() and 'reportflow_test_media_' in str(media_root):
            shutil.rmtree(media_root, ignore_errors=True)

    def login(self, username: str | None = None, password: str | None = None) -> str:
        self.clear_auth()
        response = self.client.post(
            reverse('accounts_api:login'),
            {'username': username or self.student.username, 'password': password or self.password},
            format='json',
        )
        self.assert_api_success(response, 'login')
        return response.data['data']['tokens']['access']

    def auth(self, token: str) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def clear_auth(self) -> None:
        self.client.credentials()

    def assert_api_success(self, response, label: str = '') -> None:
        prefix = f'{label}: ' if label else ''
        self.assertTrue(
            response.data.get('success'),
            f'{prefix}{response.status_code} {response.data}',
        )

    def create_report(
        self,
        *,
        student=None,
        title: str = 'API Test Report',
        status: str = Report.Status.PENDING,
        teacher_approved: bool = False,
        admin_approved: bool = False,
        is_final_submission: bool = False,
        marks: int | None = None,
    ) -> Report:
        report = Report.objects.create(
            student=student or self.student,
            title=title,
            file=dummy_pdf(f'{title.replace(" ", "_").lower()}.pdf'),
            status=status,
            teacher_approved=teacher_approved,
            admin_approved=admin_approved,
            is_final_submission=is_final_submission,
            marks=marks,
            rubric=self.rubric,
        )
        report.refresh_status_from_flags()
        report.save()
        return report

    def create_project_group(
        self,
        *,
        creator=None,
        mate=None,
        name: str = 'Test Project Group',
        assign_teacher=None,
    ) -> ProjectGroup:
        from application.services.project_group_service import ProjectGroupService

        creator = creator or self.student
        if mate is None:
            mate = User.objects.create_user(
                username=f'mate_{name.replace(" ", "_").lower()}',
                password=self.password,
                email=f'{name.replace(" ", "_").lower()}@test.com',
                role=User.Role.STUDENT,
                department=self.department_name,
                is_active=True,
            )
        service = ProjectGroupService()
        group = service.create_group(
            creator,
            {'name': name, 'project_mate_ids_list': [mate.pk]},
        )
        teacher = assign_teacher if assign_teacher is not False else None
        if teacher is not False:
            teacher = teacher or self.teacher
            service.assign_teacher(self.admin, group.pk, teacher.pk)
            group.refresh_from_db()
        return group

    def submit_group_report(
        self,
        *,
        token: str,
        group: ProjectGroup,
        title: str,
        filename: str = 'group.pdf',
    ):
        self.auth(token)
        return self.client.post(
            reverse('reports_api:submit'),
            {
                'title': title,
                'file': dummy_pdf(filename),
                'academic_year': '2025-2026',
                'submission_type': 'group',
                'project_group_id': group.pk,
            },
            format='multipart',
        )

    def create_notification(self, user=None, message: str = 'Test notification') -> Notification:
        return Notification.objects.create(
            user=user or self.student,
            message=message,
            link='/reports/my/',
        )

    def create_message(self, sender=None, receiver=None, body: str = 'Hello from API test') -> Message:
        return Message.objects.create(
            sender=sender or self.teacher,
            receiver=receiver or self.student,
            body=body,
        )

    def create_user_question(self, user=None, body: str = 'How do I submit?') -> UserQuestion:
        return UserQuestion.objects.create(
            user=user or self.student,
            subject='Submission help',
            body=body,
            status=QAItem.Status.OPEN,
        )

    def create_visitor_question(self, body: str = 'Visitor question about deadlines') -> VisitorQuestion:
        return VisitorQuestion.objects.create(
            name='Visitor',
            email='visitor@example.com',
            subject='Deadline',
            body=body,
            status=QAItem.Status.OPEN,
        )

    def create_extension_request(self, report: Report | None = None) -> DeadlineExtensionRequest:
        report = report or self.create_report()
        return DeadlineExtensionRequest.objects.create(
            report=report,
            student=report.student,
            reason='Need more time for revisions.',
            status=DeadlineExtensionRequest.Status.PENDING,
        )

    def create_reeval_request(self, report: Report | None = None) -> ReEvaluationRequest:
        report = report or self.create_report(
            status=Report.Status.APPROVED,
            teacher_approved=True,
            admin_approved=True,
            is_final_submission=True,
            marks=80,
        )
        return ReEvaluationRequest.objects.create(
            report=report,
            student=report.student,
            reason='Marks seem too low.',
            status=ReEvaluationRequest.Status.PENDING,
        )
