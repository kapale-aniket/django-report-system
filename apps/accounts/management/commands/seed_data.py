"""
Demo data: 1 admin, 10 teachers, 100 students (password Aniket123), 40 project reports,
30 with certificates (fully approved). Teachers each have 10 assigned students (round-robin).

Usage:
  python manage.py seed_data
  python manage.py seed_data --clear   # wipe non-superuser users + reports data, then seed
"""
from datetime import timedelta
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from reportlab.pdfgen import canvas

from apps.accounts.infrastructure.models import User
from apps.qa.infrastructure.models import FAQ
from apps.reports.infrastructure.models import ActivityLog, Comment, Report, ReportVersion, SystemSettings

PASSWORD = 'Aniket123'

FAQ_SEED = [
    (
        0,
        'How do I submit a project report?',
        'Log in as a student, open Submit Report from the sidebar, upload your PDF, and confirm. '
        'You can track status under My Reports.',
    ),
    (
        1,
        'What is the approval workflow?',
        'A teacher reviews your submission first, then an administrator gives final approval. '
        'You will see Pending, Approved, or Rejected on each report.',
    ),
    (
        2,
        'Who can I contact if something is wrong?',
        'If you already have an account, use Q&A in the app after you sign in. '
        'If you are not logged in yet, use the Q&A section on the public landing page.',
    ),
    (
        3,
        'Can I register without an admin account?',
        'Yes. Students and teachers can self-register from the landing page. '
        'An administrator (or your assigned teacher, for students) must approve your account before you can sign in.',
    ),
]

# 10 teachers — usernames t_01 … t_10
TEACHER_SEED = [
    ('t_01', 'Priya', 'Sharma', 'priya.sharma.seed@demo.edu'),
    ('t_02', 'Ramesh', 'Iyer', 'ramesh.iyer.seed@demo.edu'),
    ('t_03', 'Anjali', 'Nair', 'anjali.nair.seed@demo.edu'),
    ('t_04', 'Vikram', 'Joshi', 'vikram.joshi.seed@demo.edu'),
    ('t_05', 'Kavita', 'Reddy', 'kavita.reddy.seed@demo.edu'),
    ('t_06', 'Suresh', 'Menon', 'suresh.menon.seed@demo.edu'),
    ('t_07', 'Deepa', 'Krishnan', 'deepa.krishnan.seed@demo.edu'),
    ('t_08', 'Arun', 'Patel', 'arun.patel.seed@demo.edu'),
    ('t_09', 'Meera', 'Verma', 'meera.verma.seed@demo.edu'),
    ('t_10', 'Karthik', 'Sundaram', 'karthik.sundaram.seed@demo.edu'),
]

ADMIN_SEED = ('arjun_mehta', 'Arjun', 'Mehta', 'arjun.mehta@demo.edu')

FIRST_NAMES = [
    'Aarav', 'Vihaan', 'Aditya', 'Vivaan', 'Arjun', 'Reyansh', 'Muhammad', 'Sai', 'Krishna', 'Ishaan',
    'Ananya', 'Diya', 'Kavya', 'Pooja', 'Riya', 'Sneha', 'Neha', 'Ishita', 'Tanvi', 'Shruti',
]
LAST_NAMES = [
    'Sharma', 'Verma', 'Patel', 'Reddy', 'Iyer', 'Nair', 'Joshi', 'Kapoor', 'Singh', 'Kumar',
    'Gupta', 'Das', 'Bose', 'Chatterjee', 'Menon', 'Pillai', 'Rao', 'Mehta', 'Agarwal', 'Malhotra',
]

PROJECT_TOPICS = [
    'IoT Smart Irrigation',
    'ML Crop Health Prediction',
    'Blockchain Supply Chain',
    'Cloud Hospital Records',
    'Campus Attendance Mobile App',
    'Energy Analytics Dashboard',
    'NLP Chatbot for FAQs',
    'Computer Vision Quality Inspection',
    'Smart Traffic Signal Control',
    'AR Campus Navigation',
]


def pdf_bytes(title_line: str) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(400, 200))
    c.setFont('Helvetica', 12)
    c.drawString(40, 120, title_line[:80])
    c.drawString(40, 95, 'Demo PDF — Project Report System')
    c.save()
    return buf.getvalue()


class Command(BaseCommand):
    help = 'Seed demo users (100 students, 10 teachers, 1 admin), 40 reports, 30 certificates.'

    def _seed_faqs(self):
        for order, question, answer in FAQ_SEED:
            _, created = FAQ.objects.update_or_create(
                question=question,
                defaults={'answer': answer, 'sort_order': order, 'is_active': True},
            )
            self.stdout.write(
                self.style.SUCCESS(f"{'Created' if created else 'Updated'} FAQ: {question[:50]}…")
            )

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete reports-related rows and all non-superuser users before seeding.',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing reports data and non-superuser accounts...'))
            ActivityLog.objects.all().delete()
            Comment.objects.all().delete()
            ReportVersion.objects.all().delete()
            Report.objects.all().delete()
            deleted, _ = User.objects.filter(is_superuser=False).delete()
            self.stdout.write(f'Removed {deleted} user row(s). Superusers kept.')

        skip_reports = False
        if not options['clear'] and Report.objects.exists():
            skip_reports = True
            self.stdout.write(
                self.style.WARNING(
                    'Reports already exist — skipping report seed. Run: python manage.py seed_data --clear'
                )
            )

        with transaction.atomic():
            teachers = {}
            admin_user, _ = User.objects.update_or_create(
                username=ADMIN_SEED[0],
                defaults={
                    'email': ADMIN_SEED[3],
                    'first_name': ADMIN_SEED[1],
                    'last_name': ADMIN_SEED[2],
                    'role': User.Role.ADMIN,
                    'is_staff': True,
                    'is_active': True,
                    'department': 'Administration',
                },
            )
            admin_user.set_password(PASSWORD)
            admin_user.save()

            for uname, fn, ln, em in TEACHER_SEED:
                u, created = User.objects.update_or_create(
                    username=uname,
                    defaults={
                        'email': em,
                        'first_name': fn,
                        'last_name': ln,
                        'role': User.Role.TEACHER,
                        'is_staff': False,
                        'is_active': True,
                        'department': 'Computer Science',
                    },
                )
                u.set_password(PASSWORD)
                u.save()
                teachers[uname] = u
                self.stdout.write(
                    self.style.SUCCESS(f"{'Created' if created else 'Updated'} teacher: {uname}")
                )

            students = []
            for i in range(100):
                uname = f'stu_{i + 1:03d}'
                fn = FIRST_NAMES[i % len(FIRST_NAMES)]
                ln = LAST_NAMES[(i // len(FIRST_NAMES)) % len(LAST_NAMES)]
                tid = (i % 10) + 1
                tkey = f't_{tid:02d}'
                em = f'stu{i + 1:03d}@demo.edu'
                u, created = User.objects.update_or_create(
                    username=uname,
                    defaults={
                        'email': em,
                        'first_name': fn,
                        'last_name': ln,
                        'role': User.Role.STUDENT,
                        'is_staff': False,
                        'is_active': True,
                        'department': 'Computer Science',
                        'assigned_teacher': teachers[tkey],
                    },
                )
                u.set_password(PASSWORD)
                u.save()
                students.append(u)
                if created or (i + 1) % 25 == 0:
                    self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Updated'} student: {uname} -> {tkey}"))

            self._seed_faqs()

            if skip_reports:
                self.stdout.write(
                    self.style.SUCCESS('\nUsers updated. Password for all seeded accounts: Aniket123')
                )
                return

            settings_obj, _ = SystemSettings.objects.update_or_create(
                pk=1,
                defaults={
                    'submission_deadline': timezone.now() + timedelta(days=30),
                    'max_attempts': 5,
                    'max_file_size_mb': 10,
                },
            )
            self.stdout.write(self.style.SUCCESS(f'SystemSettings deadline: {settings_obj.submission_deadline}'))

            # 40 reports on first 40 students; 30 fully approved + certificate; 5 pending; 5 rejected
            for idx in range(40):
                stu = students[idx]
                topic = PROJECT_TOPICS[idx % len(PROJECT_TOPICS)]
                title = f'Final Year Project — {topic} ({stu.username})'
                fname = f'report_{stu.username}.pdf'

                if idx < 30:
                    r = Report(
                        student=stu,
                        title=title,
                        teacher_approved=True,
                        admin_approved=True,
                        certificate_generated=True,
                        is_late_submission=False,
                        marks=70 + (idx % 26),
                        teacher_marks=65 + (idx % 28),
                        feedback='Approved (seed).',
                    )
                    r.file.save(fname, ContentFile(pdf_bytes(title)), save=False)
                    r.save()
                    r.refresh_status_from_flags()
                    r.save()
                elif idx < 35:
                    r = Report(
                        student=stu,
                        title=title,
                        teacher_approved=False,
                        admin_approved=False,
                        certificate_generated=False,
                        is_late_submission=False,
                    )
                    r.file.save(fname, ContentFile(pdf_bytes(title)), save=False)
                    r.save()
                    r.refresh_status_from_flags()
                    r.save()
                else:
                    r = Report(
                        student=stu,
                        title=title,
                        status=Report.Status.REJECTED,
                        teacher_approved=False,
                        admin_approved=False,
                        certificate_generated=False,
                        rejection_reason='Seed demo: incomplete documentation.',
                        is_late_submission=False,
                    )
                    r.file.save(fname, ContentFile(pdf_bytes(title)), save=False)
                    r.save()

            # Sample comments & logs on first few reports
            qs = Report.objects.filter(student__username__startswith='stu_').order_by('id')[:5]
            rep_list = list(qs)
            if len(rep_list) >= 2:
                t = teachers['t_01']
                Comment.objects.create(
                    report=rep_list[0],
                    user=t,
                    message='Please add a sequence diagram (seed).',
                )
                ActivityLog.objects.create(
                    user=students[0],
                    action=ActivityLog.Action.SUBMITTED,
                    report=rep_list[0],
                    detail='Seed submission',
                )
            if len(rep_list) >= 1:
                ActivityLog.objects.create(
                    user=admin_user,
                    action=ActivityLog.Action.ADMIN_APPROVED,
                    report=rep_list[0],
                )

            # One version row on a rejected report if exists
            rej = Report.objects.filter(status=Report.Status.REJECTED).first()
            if rej:
                rv = ReportVersion(report=rej, version_number=1)
                rv.file.save(
                    f'{rej.student.username}_v1.pdf',
                    ContentFile(pdf_bytes('Prior draft')),
                    save=True,
                )

        self.stdout.write(self.style.SUCCESS('\nDone. Password for all seeded users: Aniket123'))
        self.stdout.write(
            'Summary: 1 admin (arjun_mehta), 10 teachers (t_01 to t_10), 100 students (stu_001 to stu_100), '
            '40 reports (30 with certificate), students assigned round-robin to teachers.'
        )
