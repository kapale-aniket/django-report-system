#!/usr/bin/env python3
"""
Generate ReportFlow interview guide PDFs.
Run: python docs/interview/generate_interview_pdfs.py
"""
from __future__ import annotations

import textwrap
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUTPUT_DIR = Path(__file__).resolve().parent

FOREST = colors.HexColor('#2d5a47')
MOSS = colors.HexColor('#4a7c59')
CLAY = colors.HexColor('#c4784a')
PARCHMENT = colors.HexColor('#faf6ee')
INK = colors.HexColor('#2c2825')
MUTED = colors.HexColor('#5c5c5c')
LIGHT_BORDER = colors.HexColor('#d8d0c4')


def build_styles():
    base = getSampleStyleSheet()
    return {
        'cover_title': ParagraphStyle(
            'CoverTitle',
            parent=base['Title'],
            fontName='Helvetica-Bold',
            fontSize=28,
            leading=34,
            textColor=FOREST,
            alignment=TA_CENTER,
            spaceAfter=14,
        ),
        'cover_sub': ParagraphStyle(
            'CoverSub',
            parent=base['Normal'],
            fontSize=13,
            leading=18,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        'section': ParagraphStyle(
            'Section',
            parent=base['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=16,
            leading=20,
            textColor=FOREST,
            spaceBefore=18,
            spaceAfter=10,
        ),
        'question': ParagraphStyle(
            'Question',
            parent=base['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=11.5,
            leading=15,
            textColor=INK,
            spaceBefore=14,
            spaceAfter=6,
            leftIndent=0,
        ),
        'answer': ParagraphStyle(
            'Answer',
            parent=base['BodyText'],
            fontName='Helvetica',
            fontSize=10.5,
            leading=15,
            textColor=INK,
            alignment=TA_JUSTIFY,
            spaceAfter=4,
            leftIndent=12,
            rightIndent=4,
        ),
        'bullet': ParagraphStyle(
            'Bullet',
            parent=base['BodyText'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=INK,
            leftIndent=24,
            bulletIndent=12,
            spaceAfter=3,
        ),
        'footer_note': ParagraphStyle(
            'FooterNote',
            parent=base['Normal'],
            fontSize=9,
            textColor=MUTED,
            alignment=TA_CENTER,
        ),
    }


def add_cover(story, styles, title: str, subtitle: str, badge: str, question_count: int):
    story.append(Spacer(1, 2.2 * cm))
    badge_table = Table(
        [[Paragraph(f'<font color="#ffffff"><b>{badge}</b></font>', styles['cover_sub'])]],
        colWidths=[8 * cm],
    )
    badge_table.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (-1, -1), MOSS),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('ROUNDEDCORNERS', [6, 6, 6, 6]),
            ]
        )
    )
    story.append(badge_table)
    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph(title, styles['cover_title']))
    story.append(Paragraph(subtitle, styles['cover_sub']))
    story.append(Spacer(1, 0.4 * cm))
    story.append(
        Paragraph(
            f'<b>{question_count} interview questions</b> with clear, detailed answers in simple English.',
            styles['cover_sub'],
        )
    )
    story.append(Spacer(1, 0.6 * cm))
    story.append(HRFlowable(width='80%', thickness=2, color=CLAY, spaceBefore=6, spaceAfter=6))
    story.append(
        Paragraph(
            'ReportFlow · Django College Report Management System<br/>'
            'Covers architecture, groups, workflow, security, API, certificates, AI &amp; more.',
            styles['cover_sub'],
        )
    )
    story.append(PageBreak())


def add_toc_hint(story, styles, sections: list[tuple[str, int]]):
    story.append(Paragraph('How to use this guide', styles['section']))
    story.append(
        Paragraph(
            'Read each question like an interviewer might ask it. The answer explains '
            '<b>what</b> the feature is, <b>why</b> we built it that way, and <b>how</b> it works in ReportFlow. '
            'Practice saying answers in your own words — do not memorize word-for-word.',
            styles['answer'],
        )
    )
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph('Sections in this PDF', styles['question']))
    for name, count in sections:
        story.append(Paragraph(f'• <b>{name}</b> — {count} questions', styles['bullet']))
    story.append(Spacer(1, 0.2 * cm))
    story.append(HRFlowable(width='100%', thickness=1, color=LIGHT_BORDER))
    story.append(PageBreak())


def add_qa_block(story, styles, number: int, question: str, answer_parts: list[str]):
    q_text = f'<font color="#2d5a47"><b>Q{number}.</b></font> {question}'
    story.append(Paragraph(q_text, styles['question']))
    for part in answer_parts:
        story.append(Paragraph(part, styles['answer']))
    story.append(Spacer(1, 0.15 * cm))


def make_pdf(filename: str, title: str, subtitle: str, badge: str, sections: list[tuple[str, list[tuple[str, list[str]]]]]):
    path = OUTPUT_DIR / filename
    styles = build_styles()
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
        title=title,
        author='ReportFlow Team',
    )

    story = []
    total_questions = sum(len(items) for _, items in sections)
    add_cover(story, styles, title, subtitle, badge, total_questions)
    add_toc_hint(story, styles, [(name, len(items)) for name, items in sections])

    question_number = 1
    for section_name, items in sections:
        story.append(Paragraph(section_name, styles['section']))
        story.append(HRFlowable(width='100%', thickness=1.5, color=MOSS, spaceAfter=8))
        for question, answer_parts in items:
            add_qa_block(story, styles, question_number, question, answer_parts)
            question_number += 1
        story.append(PageBreak())

    def draw_page(canvas, doc_obj):
        canvas.saveState()
        canvas.setFillColor(PARCHMENT)
        canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.roundRect(1.2 * cm, 1.2 * cm, A4[0] - 2.4 * cm, A4[1] - 2.4 * cm, 8, fill=1, stroke=0)
        canvas.setStrokeColor(LIGHT_BORDER)
        canvas.setLineWidth(0.5)
        canvas.roundRect(1.2 * cm, 1.2 * cm, A4[0] - 2.4 * cm, A4[1] - 2.4 * cm, 8, fill=0, stroke=1)
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(1.8 * cm, 1.0 * cm, 'ReportFlow Interview Guide')
        canvas.drawRightString(A4[0] - 1.8 * cm, 1.0 * cm, f'Page {doc_obj.page}')
        canvas.restoreState()

    doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    print(f'Created: {path}')
    return path


PROJECT_SECTIONS = [
    (
        '1. Project Overview & Architecture',
        [
            (
                'What is ReportFlow and what problem does it solve?',
                [
                    'ReportFlow is a college project report management system. Students upload PDF or DOCX project reports '
                    '(individually or in groups), teachers review them using rubrics, and administrators give final approval.',
                    'The system replaces messy email chains and spreadsheets with one place for submissions, group collaboration, '
                    'feedback, deadlines, messaging, audit logs, personalized QR-verifiable certificates, and optional AI-assisted review.',
                ],
            ),
            (
                'What is the main tech stack used in this project?',
                [
                    'Backend: <b>Django 5</b> with server-rendered templates and a <b>REST API</b> at <b>/api/v1/</b>.',
                    'Database: <b>MySQL</b>. Background jobs: <b>Celery</b> with Redis (or eager mode in development).',
                    'Auth: Django sessions for web pages and <b>JWT</b> (SimpleJWT) for API clients.',
                    'PDF/certificates: <b>ReportLab</b> and <b>qrcode</b>. Frontend: Bootstrap 5, Terra theme, vanilla JavaScript.',
                ],
            ),
            (
                'Explain the layered architecture of ReportFlow.',
                [
                    '<b>Presentation layer</b> — Django views, templates, DRF API views.',
                    '<b>Application layer</b> — services like ReportService, CertificateService, AuthService (business rules).',
                    '<b>Domain layer</b> — entities and interfaces describing core concepts.',
                    '<b>Infrastructure layer</b> — repositories, email, PDF, OCR, database helpers.',
                    'This separation keeps views thin and puts business logic in services that can be reused by both web and API.',
                ],
            ),
            (
                'Why did you choose Django for this project?',
                [
                    'Django gives built-in admin, authentication, ORM, forms, and security features out of the box.',
                    'It fits a data-heavy workflow app (reports, approvals, users, notifications) where server-side rendering '
                    'and REST API can coexist in one codebase.',
                    'Django\'s migration system and mature ecosystem (DRF, Celery integration) speed up development for a college SaaS-style product.',
                ],
            ),
            (
                'What are the three user roles and what can each role do?',
                [
                    '<b>Student</b> — register, create/join project groups, submit PDF or DOCX reports (individual or group), '
                    'track status, view group member profiles, comment, request extensions/re-evaluation, download personalized certificates.',
                    '<b>Teacher</b> — review assigned reports, score rubrics, approve/reject (with final-submission flag), '
                    'view group member portfolios, use AI insights, approve pending students, comment.',
                    '<b>Admin</b> — final approval, assign group teachers, user management, certificate template designer, '
                    'bulk actions, system settings (individual + group deadlines), audit log, extension queue, analytics.',
                    'Each role gets a different dashboard after login via role-based redirects.',
                ],
            ),
        ],
    ),
    (
        '2. Authentication, Users & Security',
        [
            (
                'How does user registration and account approval work?',
                [
                    'Students and teachers self-register from the landing page. New accounts are created with <b>is_active=False</b>.',
                    'Students need approval from their assigned teacher or an admin. Teachers need admin approval.',
                    'Until approved, login is blocked with a friendly message. Admins approve users from User Management.',
                    'Credentials can be auto-generated for admin-created users and emailed via SMTP.',
                ],
            ),
            (
                'Why use a custom User model instead of Django\'s default User?',
                [
                    'ReportFlow needs extra fields: <b>role</b> (student/teacher/admin), <b>department</b>, <b>roll_number</b>, '
                    '<b>assigned_teacher</b>, profile photo, etc.',
                    'Using AUTH_USER_MODEL = \'accounts.User\' from the start avoids painful migrations later.',
                    'All foreign keys reference one consistent user table across reports, messages, and notifications.',
                ],
            ),
            (
                'How does login work for both web pages and the API?',
                [
                    '<b>Web login</b> uses Django session authentication — a cookie keeps the user logged in.',
                    '<b>API login</b> returns JWT access + refresh tokens stored in localStorage by api_client.js.',
                    'DRF uses OptionalJWTAuthentication + SessionAuthentication — stale Bearer tokens on the login page '
                    'do not block session login (fixed in jwt_optional.py).',
                    'After login, users are redirected to the correct dashboard based on role.',
                ],
            ),
            (
                'How does ReportFlow show user-friendly error messages?',
                [
                    'Central helper: <b>core/utils/user_messages.py</b> — friendly_message() sanitizes technical errors before toasts or pages.',
                    'API defaults use plain English: "Please sign in to continue", "You don\'t have permission to do that", etc.',
                    'Frontend api_client.js maps old technical API messages via sanitizeFriendlyMessage() before ReportFlowToast.',
                    'AppError subclasses carry safe messages; raw tracebacks never reach students or teachers.',
                ],
            ),
            (
                'How do you prevent logged-out users from seeing cached pages with the back button?',
                [
                    'A custom middleware adds <b>Cache-Control: no-store</b> headers for authenticated pages.',
                    'JavaScript auth_guard.js checks session on pageshow, popstate, and visibilitychange via /accounts/session-check/.',
                    'Logout uses a redirect page that clears JWT tokens and replaces browser history.',
                    'Together these reduce the risk of seeing private data after logout using back/forward navigation.',
                ],
            ),
            (
                'What password security rules does the project enforce?',
                [
                    'Minimum length of 7 characters (project requirement for auto-generated college credentials).',
                    'Django validators block common passwords and purely numeric passwords.',
                    'Passwords are hashed with Django\'s default PBKDF2 hasher — never stored in plain text.',
                    'Password reset uses Django\'s token-based email flow with Bootstrap-styled forms.',
                ],
            ),
        ],
    ),
    (
        '3. Report Submission & Approval Workflow',
        [
            (
                'Walk through the full report lifecycle from submit to certificate.',
                [
                    '1) Student uploads PDF or DOCX (individual or group). 2) Teacher reviews with rubric scores and feedback.',
                    '3) Teacher approves and may mark <b>final submission</b>. 4) Admin gives final approval and marks.',
                    '5) If final + fully approved → personalized certificate PDF(s) with QR, email per recipient, celebration modal on dashboard.',
                    'Status: Pending → Approved or Rejected; resubmits create ReportVersion archives.',
                ],
            ),
            (
                'What file types can students submit?',
                [
                    'Reports accept <b>PDF</b> and <b>DOCX</b> (migration 0008, constants in apps/reports/constants.py).',
                    'PDFs can be previewed inline; DOCX shows a friendly "cannot preview in browser" message with download link.',
                    'AI pipeline uses document_extractor.py — PyMuPDF for PDF, zip+xml parsing for DOCX text.',
                    'Same validation (size limit, extension) applies to individual and group submissions via API and web form.',
                ],
            ),
            (
                'What happens when a student submits a report?',
                [
                    'ReportSubmitForm validates the PDF file type and size. A Report record is created linked to the student.',
                    'Default rubric is attached, academic year is set, late flag is calculated against SystemSettings deadline.',
                    'Activity log records SUBMITTED. Student and teacher get notifications.',
                    'Optional Celery task can queue AI analysis of the PDF after submission.',
                ],
            ),
            (
                'Explain the two-step approval process.',
                [
                    '<b>Step 1 — Teacher:</b> reviews PDF, fills rubric, sets teacher_marks, approves or rejects with reason.',
                    '<b>Step 2 — Admin:</b> reviews teacher-approved reports, sets final marks, admin_approved flag, final status.',
                    'This mirrors real colleges where faculty recommends and the department/admin office confirms.',
                    'Bulk admin approve/reject is supported for many reports at once.',
                ],
            ),
            (
                'What is is_final_submission and why is it important?',
                [
                    'A checkbox on teacher approval: "This is the final submission — student receives a certificate after admin approval."',
                    'Only reports marked final AND fully approved become certificate-eligible.',
                    'This prevents certificates from being issued for draft or practice submissions.',
                    'The is_certificate_eligible property checks: approved + teacher OK + admin OK + final submission.',
                ],
            ),
            (
                'How does report rejection and resubmission work?',
                [
                    'Teacher or admin can reject with a written reason stored in rejection_reason.',
                    'Rejected reports unlock for student edits unless locked. Student uploads a new PDF version.',
                    'Previous files are archived as ReportVersion records for audit/history.',
                    'Rejection emails are sent via Celery SMTP tasks; comments sync to the feedback panel.',
                ],
            ),
            (
                'What is soft delete and why use it for reports?',
                [
                    'Reports are not physically removed — is_deleted=True hides them from normal lists.',
                    'Admins can restore soft-deleted reports. Activity log records DELETED and RESTORED actions.',
                    'Soft delete protects against accidental data loss and keeps audit history intact.',
                    'Students can soft-delete their own non-approved reports; staff have broader access.',
                ],
            ),
        ],
    ),
    (
        '4. Group Projects & Collaboration',
        [
            (
                'How do project groups work in ReportFlow?',
                [
                    'Students create a <b>ProjectGroup</b> with department mates (min/max from SystemSettings).',
                    'Admin assigns a faculty guide (teacher) from Group teachers page (/reports/groups/manage/).',
                    'Only one active report per group — DB constraint prevents duplicate submissions.',
                    'ProjectGroupService in application/services/project_group_service.py handles create, list, assign_teacher.',
                ],
            ),
            (
                'How does group report submission differ from individual?',
                [
                    'Student selects submission_type=group and project_group_id on submit form or API.',
                    'Report.student is the submitter; assigned_teacher comes from group.assigned_teacher.',
                    'All group members are notified; any member can resubmit after rejection.',
                    'Group name appears on report detail, certificates, and notifications.',
                ],
            ),
            (
                'How can teachers and students view group member profiles?',
                [
                    'Report detail has a <b>Student profiles</b> button → /reports/&lt;pk&gt;/member-profiles/.',
                    'Shows each member\'s photo, roll number, department, and link to public portfolio.',
                    'Public portfolio: /reports/student/&lt;username&gt;/ (student_profile_public.html).',
                    'Teachers assigned to the group can view any mate\'s full profile for review context.',
                ],
            ),
            (
                'What does the Project groups page show to students?',
                [
                    'My groups and Public groups lists with <b>comma-separated member names</b> plus member count.',
                    'Template: templates/reports/project_groups.html. Sidebar nav section for students.',
                    'Students create groups from /reports/groups/create/ with mate multi-select (project_group_create.js).',
                    'API mirror: /api/v1/project-groups/ (list, create, submittable, assign-teacher).',
                ],
            ),
        ],
    ),
    (
        '5. Certificates, QR Verification & PDF',
        [
            (
                'How does the QR certificate feature work?',
                [
                    'When eligible, CertificateService generates a landscape PDF using ReportLab (certificate_builder.py).',
                    'Each certificate gets a unique verification code in certificate_verification_code (submitter) '
                    'or certificate_member_codes_json for other group members.',
                    'QR code links to public page: /certificates/verify/?code=... (absolute URL via SITE_BASE_URL).',
                    'Verify page supports manual code entry and QR scan from uploaded image/PDF (certificate_verify.js).',
                ],
            ),
            (
                'How do personalized certificates work for group projects?',
                [
                    'On admin approval, ensure_all_recipient_codes() assigns a unique token per group member.',
                    'Submitter uses report.certificate_verification_code; mates use certificate_member_codes_json[user_id].',
                    'Each PDF shows that member\'s name, roll number, project title, group name, and their own QR.',
                    'Certificate email loop sends one personalized PDF attachment per recipient via Celery.',
                ],
            ),
            (
                'What is the certificate celebration modal?',
                [
                    'After certificate_generated=True, students see a confetti modal on the student dashboard.',
                    'Model: CertificateCelebrationAcknowledgment — tracks who has acknowledged per report.',
                    'Modal: templates/dashboard/partials/certificate_celebration_modal.html + certificate_celebration.js.',
                    'Ack POST to /reports/&lt;pk&gt;/certificate-celebration/ack/ hides modal until next certificate.',
                    'Every group member gets their own celebration when they log in (not just the submitter).',
                ],
            ),
            (
                'Explain the admin certificate template designer.',
                [
                    'Admin dashboard embeds CertificateTemplateForm with multi-tab designer (Start, Colors, Typography, etc.).',
                    'Upload reference image → analyze endpoint extracts palette, blur check, suggested design_json.',
                    'CertificateTemplateService + certificate_template_analyzer.py; preview before save without persisting.',
                    'Multiple templates in library; activate one for all new certificates. Missing image files fail gracefully.',
                ],
            ),
            (
                'What conditions must be met before a certificate is issued?',
                [
                    'Report status must be Approved. teacher_approved and admin_approved must both be True.',
                    'is_final_submission must be True (teacher checkbox).',
                    'CertificateService.build_pdf_bytes() validates eligibility before generating PDF.',
                    'issue_certificate_if_eligible() sends email with PDF attachment and in-app notification.',
                ],
            ),
            (
                'Why use absolute URLs inside QR codes?',
                [
                    'Phone cameras need a full https:// URL to open the verify page, not a relative /path.',
                    'SITE_BASE_URL setting builds the link embedded in the QR (e.g. https://college.edu/certificates/verify/?code=...).',
                    'Without absolute URLs, scanning would fail outside the app context.',
                ],
            ),
            (
                'What libraries generate the certificate PDF and QR image?',
                [
                    '<b>ReportLab</b> draws the landscape certificate: borders, grades, chips, signatures area.',
                    '<b>qrcode[pil]</b> generates the QR PNG embedded in the PDF.',
                    'CertificateContext dataclass holds student name, project title, marks, dates, verify URL.',
                    'PDF bytes are returned to browser download or attached to certificate email.',
                ],
            ),
        ],
    ),
    (
        '6. API, Services & Background Jobs',
        [
            (
                'Describe the REST API structure.',
                [
                    'Base path: <b>/api/v1/</b>. Modules: auth, reports, project-groups, messaging, qa, dashboard, certificates.',
                    'API uses standard envelope: { success, message, data, errors, status_code }.',
                    'OpenAPI docs at /api/docs/ via drf-spectacular (Swagger UI).',
                    'List endpoints support pagination, search, filtering, and ordering.',
                ],
            ),
            (
                'How many automated tests does the project have?',
                [
                    'About <b>70 tests</b> across api/tests/, core/tests/, and infrastructure/ai/tests/.',
                    'Includes EndToEndApprovalFlowTests (submit → approve → certificate → celebration), '
                    'group certificate tests, member profile tests, and UserFriendlyMessageTests.',
                    'Run: python manage.py test. APITestBase in api/tests/base.py provides shared fixtures.',
                ],
            ),
            (
                'What is the repository pattern used in this project?',
                [
                    'Repositories (e.g. ReportRepository, NotificationRepository) encapsulate database queries.',
                    'Services call repositories instead of scattering ORM code everywhere.',
                    'Benefits: easier testing, consistent filters, one place to change query logic.',
                    'Example: apply_search_filters() mirrors ReportFilterForm params for API and web.',
                ],
            ),
            (
                'How are background tasks handled with Celery?',
                [
                    'Celery tasks: send_certificate_email, send_rejection_email, notify_user, process_report_ai.',
                    'tasks/dispatch.py checks CELERY_TASK_ALWAYS_EAGER — in dev tasks run synchronously without Redis.',
                    'In production, Redis broker queues tasks so slow work (email, AI) does not block HTTP requests.',
                    'Task names like reportflow.send_certificate_email make monitoring easy.',
                ],
            ),
            (
                'How do in-app notifications work?',
                [
                    'Notification model stores message, link, is_read, user, type=ALERT.',
                    'create_in_app_notification() writes directly for synchronous web views.',
                    'queue_user_notification() queues Celery task for async delivery in services.',
                    'Bell icon in navbar shows unread count; clicking marks read and navigates to linked page.',
                ],
            ),
            (
                'What is logged in the activity audit trail?',
                [
                    'ActivityLog records user, action type (SUBMITTED, ADMIN_APPROVED, DELETED, etc.), report, detail text, timestamp.',
                    'Admins view/filter logs in the Activity Log viewer.',
                    'Supports accountability — who approved, rejected, or changed what and when.',
                    'Important for college compliance and debugging disputes.',
                ],
            ),
        ],
    ),
    (
        '7. Other Modules & Practical Topics',
        [
            (
                'How does the messaging module work?',
                [
                    'Simple internal inbox: users send messages to each other with subject and body.',
                    'Inbox and Sent views with sorting and pagination. mark_read for unread tracking.',
                    'MessagingService and MessageRepository back the API; templates provide compose modal.',
                    'Unread count appears in navbar via context processor.',
                ],
            ),
            (
                'Explain the Q&A and visitor ask feature.',
                [
                    'Logged-in users ask questions; admins reply from qa/home.html queue.',
                    'Landing page visitors submit questions via modal — stored as VisitorQuestion, emailed on reply.',
                    'FAQ model powers accordion on landing page for common answers.',
                    'Separates authenticated help desk from public pre-login inquiries.',
                ],
            ),
            (
                'What is re-evaluation and how is it handled?',
                [
                    'After full approval, students can request re-evaluation if they disagree with marks.',
                    'ReEvaluationRequest stores reason, status PENDING/APPROVED/REJECTED, updated_marks.',
                    'Admins resolve from report detail; approved requests update report.marks.',
                    'Notifications inform student and log REEVAL_REQUESTED / REEVAL_RESOLVED in activity log.',
                ],
            ),
            (
                'What is a deadline extension request?',
                [
                    'Students request more time when submission_deadline in SystemSettings has passed or is near.',
                    'DeadlineExtensionRequest goes to admin extension queue for approve/reject.',
                    'Approved extensions can extend global deadline (demo: +7 days in settings).',
                    'Prevents hard failures when legitimate delays occur.',
                ],
            ),
            (
                'How does the leaderboard feature work?',
                [
                    'Shows top approved reports by marks, filterable by department.',
                    'Teachers see assigned students; students see their department ranking.',
                    'LeaderboardService aggregates Report queryset with marks__isnull=False.',
                    'Motivates students and gives teachers a quick performance snapshot.',
                ],
            ),
            (
                'What database does the project use and why MySQL?',
                [
                    'MySQL with utf8mb4 charset for full Unicode support (names, project titles).',
                    'Strict SQL mode enabled via init_command for safer data integrity.',
                    'Common in college/enterprise environments; Django ORM abstracts most raw SQL.',
                    'PyMySQL driver connects Django to MySQL on localhost in development settings.',
                ],
            ),
            (
                'How would you deploy ReportFlow to production?',
                [
                    'Use Gunicorn/uWSGI + Nginx, set DEBUG=False, strong SECRET_KEY, ALLOWED_HOSTS, SITE_BASE_URL.',
                    'Store SMTP and DB credentials in environment variables, not in code.',
                    'Run Celery workers + Redis for async email/AI. Collect static files (collectstatic).',
                    'Enable HTTPS, regular DB backups, and monitor logs in logs/reportflow.log.',
                ],
            ),
            (
                'What were the biggest technical challenges in this project?',
                [
                    'Coordinating multi-role approval state (teacher_approved, admin_approved, status flags) without inconsistency.',
                    'Group certificates — unique QR per member, personalized PDFs, verify lookup for member codes.',
                    'Certificate template designer — image analyzer, missing-file resilience, preview-before-save.',
                    'Keeping web views and REST API in sync through shared service layer; friendly user messages everywhere.',
                ],
            ),
            (
                'How do you explain ReportFlow in a 30-second elevator pitch?',
                [
                    '"ReportFlow is a college platform where students submit project PDFs or Word files — solo or in groups — '
                    'teachers grade with rubrics and optional AI assist, admins finalize approval, and the system auto-generates '
                    'personalized QR-verifiable certificates with a celebration moment, plus messaging, audit logs, and group collaboration."',
                    'Emphasize: structured workflow, group support, trust via audit trail and verifiable certificates.',
                ],
            ),
            (
                'How are uploaded PDF files stored and served?',
                [
                    'Django FileField on Report model saves files under MEDIA_ROOT (media/reports/...).',
                    'MEDIA_URL serves files in DEBUG mode; production uses Nginx or cloud storage (S3-compatible).',
                    'view_pdf streams PDF inline with FileResponse after permission check (_can_view_report).',
                    'Only authorized roles (owner, assigned teacher, admin) can open or download files.',
                ],
            ),
            (
                'What is the purpose of ReportVersion and version compare?',
                [
                    'Each resubmit archives the old PDF as a ReportVersion with version_number increment.',
                    'version_compare view lets staff select two versions side-by-side for audit.',
                    'Helps teachers see what changed between reject and resubmit.',
                    'Supports academic integrity investigations without losing history.',
                ],
            ),
            (
                'How does role-based permission work in API views?',
                [
                    'Custom DRF permission classes: IsStudent, IsTeacher, IsAdmin in api/permissions/.',
                    'Each API view sets permission_classes — e.g. only admin can bulk approve.',
                    'Services double-check role logic for defense in depth (PermissionAppError).',
                    'Same rules apply in Django views via @role_required decorator.',
                ],
            ),
            (
                'What is the standard API response envelope and why use it?',
                [
                    'Every API response: { success: true/false, message, data, errors, status_code }.',
                    'Frontend api_client.js expects this format for toast messages and redirects.',
                    'Consistent errors help AJAX forms show user-friendly messages without parsing HTML.',
                    'Implemented in core/api_response/APIResponse.py and BaseAPIView.',
                ],
            ),
            (
                'What frontend JavaScript modules power the UI?',
                [
                    '<b>api_client.js</b> — JWT login, AJAX forms, sanitizeFriendlyMessage for toasts.',
                    '<b>toast.js</b> — 5-second notification toasts. <b>auth_guard.js</b> — session security.',
                    '<b>certificate_designer.js</b> — template analyze/preview. <b>certificate_celebration.js</b> — confetti modal ack.',
                    '<b>certificate_verify.js</b> — QR scan from image/PDF. <b>submit_group.js</b> / project_group_create.js — group flows.',
                    '<b>report_ai.js</b> — teacher AI insights. <b>rf_table.js</b> — table search/sort/pagination.',
                ],
            ),
            (
                'How does the Terra theme differ from default Bootstrap?',
                [
                    'Custom CSS variables: terra-forest, terra-moss, terra-clay, terra-parchment palette.',
                    'Source Serif 4 for headings, DM Sans for body — warm academic look not generic Bootstrap blue.',
                    'app-card, terra-badge, terra-panel-accent components used across dashboard and landing.',
                    'Dark mode via data-bs-theme attribute synced with localStorage.',
                ],
            ),
        ],
    ),
]


AI_SECTIONS = [
    (
        '1. AI Features Overview',
        [
            (
                'What AI features does ReportFlow provide?',
                [
                    '<b>AI Report Analysis</b> — extract PDF/DOCX text, run OCR on scans if needed, verify PDF quality, '
                    'generate summary and rubric score suggestions for teachers.',
                    '<b>AI Q&A assistant</b> — optional AI-powered help for user questions (AIReportService / AIQAService).',
                    'AI is assistive only — teachers and admins always make final decisions; AI does not auto-approve reports.',
                    'Controlled by AI_FEATURES_ENABLED setting and runs mainly on teacher request or background Celery task.',
                ],
            ),
            (
                'Why add AI to a report management system?',
                [
                    'Teachers spend long hours reading lengthy PDFs. AI gives a quick summary and draft rubric scores to speed review.',
                    'OCR verification catches scanned/low-quality PDFs where text extraction fails.',
                    'Reduces repetitive work while keeping human judgment for marks and approval.',
                    'Demonstrates modern full-stack skills: LLM integration, PDF pipeline, async processing.',
                ],
            ),
            (
                'Where is AI code located in the project structure?',
                [
                    '<b>application/services/ai_report_service.py</b> — main orchestration.',
                    '<b>infrastructure/ai/document_extractor.py</b> — routes PDF vs DOCX extraction.',
                    '<b>infrastructure/ai/pdf_extractor.py</b> — native PDF text via PyMuPDF.',
                    '<b>infrastructure/ai/llm_client.py</b> — OpenAI/HTTP LLM calls with JSON response.',
                    '<b>infrastructure/ocr/pdf_ocr.py</b> — Tesseract OCR fallback (PDF only).',
                    '<b>tasks/celery_tasks/ai_tasks.py</b> — process_report_ai_task for async runs.',
                ],
            ),
        ],
    ),
    (
        '2. PDF Extraction & OCR Pipeline',
        [
            (
                'Explain the full AI report analysis pipeline step by step.',
                [
                    '1) Load report file (PDF or DOCX) from disk. 2) Extract text — PyMuPDF for PDF, zip+xml for DOCX (document_extractor.py).',
                    '3) For PDF only: if native text is short, run OCR with pytesseract on page images.',
                    '4) verify_pdf_text() compares native vs OCR to detect scan quality issues (PDF only).',
                    '5) Send extracted text + rubric criteria to LLM (or heuristic fallback). 6) Save on Report JSON fields.',
                ],
            ),
            (
                'Does AI work on DOCX submissions?',
                [
                    'Yes. document_extractor.py detects file type and reads word/document.xml from the DOCX zip.',
                    'OCR verification applies to PDF only — DOCX skips verify_pdf_text() but still gets LLM/heuristic analysis.',
                    'Teachers see the same AI insights panel on report detail for both PDF and DOCX reports.',
                    'If extraction fails, ai_processing_status=FAILED with a friendly error; manual review still works.',
                ],
            ),
            (
                'What is PyMuPDF used for in this project?',
                [
                    'PyMuPDF (fitz) reads PDF files and extracts embedded text without OCR.',
                    'It is faster and more accurate than OCR when students submit proper digital PDFs.',
                    'Returns text, page count, and char count capped by AI_MAX_PDF_TEXT_CHARS setting.',
                    'First choice in the pipeline — OCR only when native extraction is insufficient.',
                ],
            ),
            (
                'When and why is OCR (Tesseract) used?',
                [
                    'OCR runs when native text has fewer characters than AI_OCR_MIN_NATIVE_CHARS (default 400).',
                    'Common for scanned reports photographed or printed and uploaded as PDF.',
                    'pytesseract converts PDF pages to images then reads text.',
                    'Slower and less accurate than native text — but necessary for image-based PDFs.',
                ],
            ),
            (
                'What does verify_pdf_text() do?',
                [
                    'Compares native extracted text with OCR text to assess PDF quality.',
                    'Stores results in report.ocr_verification_json: match score, warnings, page count, processed_at.',
                    'Helps teachers see if the PDF is searchable/digital or a low-quality scan.',
                    'Teachers can ask students to resubmit a proper PDF if verification fails badly.',
                ],
            ),
            (
                'What is stored in extracted_text, ai_analysis_json, and ocr_verification_json?',
                [
                    '<b>extracted_text</b> — plain text from PDF (native or OCR) or DOCX used for AI and display.',
                    '<b>ai_analysis_json</b> — summary, suggested_criterion_scores, suggested_feedback, suggested_teacher_marks, provider, generated_at.',
                    '<b>ocr_verification_json</b> — quality metrics from verify_pdf_text().',
                    '<b>ai_processing_status</b> — PENDING, PROCESSING, COMPLETED, or FAILED.',
                ],
            ),
        ],
    ),
    (
        '3. LLM Integration & Teacher Insights',
        [
            (
                'How does the LLM client work?',
                [
                    'LLMClient in infrastructure/ai/llm_client.py wraps HTTP calls to OpenAI-compatible API via httpx.',
                    'chat_json(system_prompt, user_prompt) asks the model to return strict JSON.',
                    'If API key missing or call fails, heuristic_report_analysis() provides rule-based fallback.',
                    'Keeps AI optional — app works fully without any LLM configured.',
                ],
            ),
            (
                'What JSON does the LLM return for report analysis?',
                [
                    'Expected keys: summary, suggested_criterion_scores (map of criterion id → score), '
                    'suggested_feedback (text), suggested_teacher_marks (0–100 integer).',
                    'System prompt instructs model to stay concise and respect rubric max scores.',
                    'Response is parsed, validated, and normalized before saving to ai_analysis_json.',
                ],
            ),
            (
                'What is get_teacher_insights() and when is it called?',
                [
                    'API/service method that returns AI summary, OCR verification, rubric suggestions for a report.',
                    'Only teachers and admins can access — permission check in AIReportService.',
                    'If status is PENDING, it triggers analyze_report_pdf() first then refresh_from_db().',
                    'Frontend report_ai.js displays insights panel on teacher report detail page.',
                ],
            ),
            (
                'Does AI auto-approve or auto-reject reports?',
                [
                    '<b>No.</b> AI only suggests — teacher must manually enter marks, feedback, and click approve/reject.',
                    'This is intentional for academic integrity and legal accountability.',
                    'AI suggestions pre-fill forms optionally; final submission checkbox remains teacher\'s decision.',
                    'Good answer in interviews: "AI assists, humans decide."',
                ],
            ),
            (
                'How are AI failures handled gracefully?',
                [
                    'On exception, ai_processing_status = FAILED and ai_analysis_json stores a safe error message.',
                    'Exception is logged to reportflow.ai logger. API returns user-friendly copy via user_messages / AppError.',
                    'Teacher can still review PDF/DOCX manually — AI failure never blocks approval workflow.',
                    'Retry possible by calling analyze again after fixing API key or file issue.',
                ],
            ),
        ],
    ),
    (
        '4. Async Processing, Settings & Security',
        [
            (
                'How is AI processing run asynchronously?',
                [
                    'queue_report_ai_analysis(report_id) in tasks/dispatch.py enqueues Celery task.',
                    'process_report_ai_task calls AIReportService().analyze_report_pdf(report_id).',
                    'In development CELERY_TASK_ALWAYS_EAGER=True runs task immediately in same process.',
                    'Production uses Redis broker so long PDF+LLM work does not timeout HTTP request.',
                ],
            ),
            (
                'What settings control AI behavior?',
                [
                    '<b>AI_FEATURES_ENABLED</b> — master switch to disable all AI endpoints.',
                    '<b>AI_MAX_PDF_TEXT_CHARS</b> — limits text sent to LLM (cost + token control).',
                    '<b>AI_OCR_MIN_NATIVE_CHARS</b> — threshold to trigger OCR fallback.',
                    'OpenAI API key and model name from environment variables — never hard-coded in repo.',
                ],
            ),
            (
                'What data is sent to the external LLM and what privacy concerns exist?',
                [
                    'Sent: report title, rubric criteria names/max scores, extracted report text from PDF or DOCX (truncated).',
                    'Not sent: passwords, unrelated student records, admin settings.',
                    'For production colleges: need student consent, data processing agreement, possibly anonymize names.',
                    'Can disable AI entirely with AI_FEATURES_ENABLED=False for strict privacy policies.',
                ],
            ),
            (
                'Explain AIQAService / AI-assisted Q&A if asked.',
                [
                    'Separate from report analysis — helps answer user or visitor questions using LLM + FAQ context.',
                    'Uses ai_qa_service.py and api serializers; may suggest draft admin replies.',
                    'Keeps human admin in the loop for published answers — similar assist-only pattern.',
                    'Shows extensibility of LLMClient beyond PDF grading.',
                ],
            ),
        ],
    ),
    (
        '5. Interview Deep-Dive (AI Scenario Questions)',
        [
            (
                'How would you improve the AI module in version 2?',
                [
                    'Add chunking for very long PDFs with map-reduce summarization.',
                    'Cache analysis results by file hash to avoid re-processing unchanged resubmissions.',
                    'Support local/on-prem LLM (Ollama) for colleges that ban cloud AI.',
                    'Show confidence scores and highlight PDF sections used for each rubric suggestion.',
                ],
            ),
            (
                'How do you test AI features without spending API money?',
                [
                    'Use heuristic_report_analysis() fallback when OPENAI_API_KEY is unset.',
                    'CELERY_TASK_ALWAYS_EAGER=True for synchronous tests in development.',
                    'Mock LLMClient in unit tests to return fixed JSON.',
                    'Test OCR path with sample scanned PDF fixtures in media/test/.',
                ],
            ),
            (
                'What is the difference between native PDF text and OCR text?',
                [
                    'Native text comes from PDF\'s embedded character map — exact, selectable, fast.',
                    'OCR guesses text from pixels — errors on handwriting, skew, low resolution.',
                    'ReportFlow prefers native; OCR is fallback and quality-check reference.',
                    'Interview tip: mention you understand both digital-first and scan-first student submissions.',
                ],
            ),
            (
                'Why cap extracted text at AI_MAX_PDF_TEXT_CHARS?',
                [
                    'LLM APIs charge by tokens — long theses could be expensive.',
                    'Model context windows have limits — truncating prevents API errors.',
                    'First N characters usually contain abstract, introduction, conclusion cues for summary.',
                    'Setting is configurable per deployment size (small college vs research university).',
                ],
            ),
            (
                'Describe ai_processing_status state machine.',
                [
                    '<b>PENDING</b> — never analyzed yet. <b>PROCESSING</b> — job running now.',
                    '<b>COMPLETED</b> — success, JSON fields populated. <b>FAILED</b> — error stored, manual review still OK.',
                    'Status shown in teacher UI so they know if suggestions are fresh or unavailable.',
                    'Simple enum on Report model — easy to query and display.',
                ],
            ),
            (
                'How would you explain AIReportService in one paragraph to a non-technical interviewer?',
                [
                    '"When a teacher opens AI insights, the system reads the student\'s PDF or Word file, checks if the text is clear (PDF scans), '
                    'and sends a shortened version to an AI model along with the grading rubric. '
                    'The AI returns a plain-English summary and suggested scores. The teacher reads everything and '
                    'decides the real marks — the AI is like a smart assistant, not the final judge."',
                ],
            ),
            (
                'What libraries would you mention for AI/PDF in this project?',
                [
                    '<b>PyMuPDF</b> — PDF text extraction. <b>pytesseract</b> — OCR (PDF scans). <b>Pillow</b> — images for QR, OCR, certificate analyzer.',
                    '<b>httpx</b> — HTTP to LLM API. <b>Celery</b> — background analysis and certificate emails.',
                    '<b>ReportLab</b> + <b>qrcode</b> — certificate PDF generation (separate from AI but often asked together).',
                    'DOCX text uses Python zipfile + XML parsing — no python-docx dependency required.',
                ],
            ),
            (
                'Can the app run without installing Tesseract or OpenAI?',
                [
                    'Yes. Core report workflow (submit, approve, certificate) needs neither.',
                    'Without Tesseract: OCR path fails gracefully; digital PDFs still work via PyMuPDF.',
                    'Without OpenAI: heuristic_report_analysis() gives basic keyword-based suggestions.',
                    'AI is an enhancement layer — good architecture keeps core features independent.',
                ],
            ),
        ],
    ),
]


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    project_total = sum(len(items) for _, items in PROJECT_SECTIONS)
    ai_total = sum(len(items) for _, items in AI_SECTIONS)
    make_pdf(
        'ReportFlow_Project_Interview_Guide.pdf',
        'ReportFlow Project<br/>Interview Guide',
        'Architecture · Groups · Workflow · Security · API · Certificates',
        f'GENERAL — {project_total} QUESTIONS',
        PROJECT_SECTIONS,
    )
    make_pdf(
        'ReportFlow_AI_Interview_Guide.pdf',
        'ReportFlow AI Module<br/>Interview Guide',
        'PDF/DOCX Pipeline · OCR · LLM · Celery · Privacy · Best Practices',
        f'AI FOCUS — {ai_total} QUESTIONS',
        AI_SECTIONS,
    )


if __name__ == '__main__':
    main()
