from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace

from django.conf import settings
from django.core.validators import FileExtensionValidator

from apps.reports.constants import ALLOWED_REPORT_EXTENSIONS, report_file_extension
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone


def report_upload_path(instance, filename):
    return f'reports/user_{instance.student_id}/{filename}'


def version_upload_path(instance, filename):
    return f'report_versions/report_{instance.report_id}/v{instance.version_number}_{filename}'


# Status badge metadata (replaces ReportStatusDefinition table).
STATUS_BADGES = {
    'pending': {'label': 'Pending', 'badge_class': 'secondary', 'icon': 'bi-hourglass-split'},
    'under_review': {'label': 'Under Review', 'badge_class': 'warning', 'icon': 'bi-eye'},
    'awaiting_admin': {'label': 'Awaiting admin', 'badge_class': 'info', 'icon': 'bi-shield-check'},
    'approved': {'label': 'Approved', 'badge_class': 'success', 'icon': 'bi-check-circle'},
    'rejected': {'label': 'Rejected', 'badge_class': 'danger', 'icon': 'bi-x-circle'},
    'needs_fix': {'label': 'Needs fix', 'badge_class': 'warning', 'icon': 'bi-wrench-adjustable'},
}


class SystemSettings(models.Model):
    """Singleton (pk=1): deadlines, upload limits, attempt caps."""

    submission_deadline = models.DateTimeField(
        help_text='Individual project submissions after this instant are marked late.',
    )
    max_attempts = models.PositiveIntegerField(
        default=5,
        help_text='Max resubmission attempts for individual projects.',
    )
    max_file_size_mb = models.PositiveIntegerField(default=10)
    group_submission_deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Group project deadline. Falls back to the individual deadline when empty.',
    )
    group_max_attempts = models.PositiveIntegerField(
        default=5,
        help_text='Max resubmission attempts for group projects.',
    )
    group_min_members = models.PositiveIntegerField(
        default=2,
        help_text='Minimum members in a project group (including the creator).',
    )
    group_max_members = models.PositiveIntegerField(
        default=6,
        help_text='Maximum members in a project group (including the creator).',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'System settings'

    def __str__(self):
        return f'Settings · deadline {self.submission_deadline}'

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                'submission_deadline': timezone.now() + timedelta(days=365),
                'max_attempts': 5,
                'max_file_size_mb': 10,
                'group_max_attempts': 5,
                'group_min_members': 2,
                'group_max_members': 6,
            },
        )
        return obj


def certificate_template_upload_path(instance, filename):
    return f'certificate_templates/{instance.pk or "new"}_{filename}'


class CertificateTemplate(models.Model):
    """Active certificate layout — fully configurable by admin."""

    name = models.CharField(max_length=200, default='Official certificate')
    is_active = models.BooleanField(default=True, db_index=True)
    reference_image = models.ImageField(
        upload_to=certificate_template_upload_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
        help_text='Background / reference image (PNG/JPG/WEBP).',
    )
    organization_logo = models.ImageField(
        upload_to=certificate_template_upload_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
    )
    watermark_image = models.ImageField(
        upload_to=certificate_template_upload_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
    )
    seal_image = models.ImageField(
        upload_to=certificate_template_upload_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
    )
    signature_image = models.ImageField(
        upload_to=certificate_template_upload_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
    )
    achievement_badge = models.ImageField(
        upload_to=certificate_template_upload_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
    )
    title_text = models.CharField(max_length=120, default='Certificate of Completion')
    subtitle_text = models.CharField(max_length=200, default='This is to certify that')
    organization_name = models.CharField(max_length=160, blank=True, default='ReportFlow')
    tagline = models.CharField(max_length=220, blank=True, default='Official Project Completion Record')
    footer_text = models.CharField(
        max_length=220,
        default='Approved by faculty and administration · Final submission verified',
    )
    description_template = models.CharField(
        max_length=260,
        blank=True,
        default='has successfully completed the final project submission',
    )
    accent_color = models.CharField(max_length=7, default='#2d5a47')
    secondary_color = models.CharField(max_length=7, default='#c9a227')
    text_color = models.CharField(max_length=7, default='#2c2c2c')
    muted_color = models.CharField(max_length=7, default='#5c5c5c')
    background_color = models.CharField(max_length=7, default='#faf6ee')
    border_color = models.CharField(max_length=7, default='#2d5a47', blank=True)
    name_color = models.CharField(max_length=7, default='#2d5a47', blank=True)
    name_font = models.CharField(max_length=40, default='Helvetica-Bold', blank=True)
    name_size = models.PositiveSmallIntegerField(default=22)
    use_reference_background = models.BooleanField(
        default=True,
        help_text='When enabled, the background image fills the certificate.',
    )
    design_json = models.JSONField(default=dict, blank=True)
    style_json = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='certificate_templates_updated',
    )

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.name

    @classmethod
    def get_active(cls):
        template = cls.objects.filter(is_active=True).order_by('-updated_at').first()
        if template:
            return template
        return cls.objects.create(name='Default ReportFlow certificate', is_active=True)

    @classmethod
    def activate(cls, template: 'CertificateTemplate') -> None:
        cls.objects.exclude(pk=template.pk).update(is_active=False)
        if not template.is_active:
            template.is_active = True
            template.save(update_fields=['is_active'])


class ProjectGroup(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    department = models.CharField(max_length=120, blank=True, db_index=True)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_project_groups',
    )
    assigned_teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_project_groups',
        limit_choices_to={'role': 'teacher'},
        help_text='Faculty guide for this group — assigned by admin based on department.',
    )
    is_public = models.BooleanField(
        default=True,
        db_index=True,
        help_text='Public groups are visible to all students after creation.',
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='project_groups',
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', 'name']

    def __str__(self):
        return self.name

    def get_active_report(self):
        return self.reports.filter(is_deleted=False).order_by('-submitted_at').first()

    @property
    def has_active_submission(self) -> bool:
        return self.reports.filter(is_deleted=False).exists()

    @property
    def member_count(self) -> int:
        return self.members.count()


class Rubric(models.Model):
    name = models.CharField(max_length=200)
    is_default = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=True)
    criteria_json = models.JSONField(
        default=list,
        blank=True,
        help_text='List of {id, name, max_score, sort_order} criterion definitions.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_criteria(self) -> list[dict]:
        rows = self.criteria_json or []
        return sorted(rows, key=lambda row: (row.get('sort_order', 0), row.get('id', 0)))

    def iter_criteria(self):
        for row in self.get_criteria():
            yield SimpleNamespace(
                pk=row.get('id'),
                name=row.get('name', ''),
                max_score=row.get('max_score', 0),
                sort_order=row.get('sort_order', 0),
            )


class Report(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    class SubmissionRound(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        REVIEW = 'review', 'Review'
        FINAL = 'final', 'Final'

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reports',
    )
    assigned_teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_reports',
        limit_choices_to={'role': 'teacher'},
        help_text='Faculty guide for this project. Each report can have a different teacher.',
    )
    title = models.CharField(max_length=255)
    file = models.FileField(
        upload_to=report_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=list(ALLOWED_REPORT_EXTENSIONS))],
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    teacher_approved = models.BooleanField(default=False)
    admin_approved = models.BooleanField(default=False)
    rejection_reason = models.TextField(blank=True)
    is_late_submission = models.BooleanField(default=False)
    certificate_generated = models.BooleanField(default=False)
    is_final_submission = models.BooleanField(
        default=False,
        help_text='Teacher marks this as the final submission; certificate is issued after admin approval.',
    )
    certificate_verification_code = models.CharField(
        max_length=64,
        blank=True,
        default='',
        db_index=True,
        help_text='Unique token for QR certificate verification.',
    )
    certificate_member_codes_json = models.JSONField(
        default=dict,
        blank=True,
        help_text='Map of group member user id (str) to personal certificate verification codes.',
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    marks = models.PositiveIntegerField(null=True, blank=True)
    teacher_marks = models.PositiveIntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    submission_round = models.CharField(
        max_length=20,
        choices=SubmissionRound.choices,
        default=SubmissionRound.REVIEW,
        db_index=True,
    )
    is_locked = models.BooleanField(default=False, db_index=True)
    attempt_count = models.PositiveIntegerField(default=1)
    is_deleted = models.BooleanField(default=False, db_index=True)
    tags = models.CharField(max_length=500, blank=True)
    group = models.ForeignKey(
        ProjectGroup,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reports',
    )
    rubric = models.ForeignKey(
        Rubric,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reports',
    )
    rubric_scores_json = models.JSONField(
        default=dict,
        blank=True,
        help_text='Map of criterion id (str) to score.',
    )
    is_pinned = models.BooleanField(default=False, db_index=True)
    academic_year = models.CharField(max_length=16, blank=True, db_index=True)
    is_archived = models.BooleanField(default=False, db_index=True)
    extracted_text = models.TextField(
        blank=True,
        default='',
        help_text='Native text extracted from the submitted report file.',
    )
    ai_analysis_json = models.JSONField(
        default=dict,
        blank=True,
        help_text='AI summary and suggested rubric scores for teacher review.',
    )
    ocr_verification_json = models.JSONField(
        default=dict,
        blank=True,
        help_text='OCR vs native text verification metadata.',
    )

    class AIProcessingStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    ai_processing_status = models.CharField(
        max_length=20,
        choices=AIProcessingStatus.choices,
        default=AIProcessingStatus.PENDING,
        db_index=True,
    )

    class Meta:
        ordering = ['-is_pinned', '-submitted_at']
        constraints = [
            models.UniqueConstraint(
                fields=['group'],
                condition=models.Q(group__isnull=False),
                name='report_unique_group_when_set',
            ),
        ]

    def __str__(self):
        return f'{self.title} — {self.student}'

    @property
    def file_extension(self) -> str:
        if not self.file:
            return ''
        return report_file_extension(self.file.name)

    @property
    def is_pdf_file(self) -> bool:
        return self.file_extension == 'pdf'

    def get_status_slug(self) -> str:
        if self.status == self.Status.REJECTED:
            return 'rejected'
        if self.status == self.Status.APPROVED:
            return 'approved'
        if self.teacher_approved and not self.admin_approved:
            return 'awaiting_admin'
        if self.status == self.Status.PENDING and not self.teacher_approved:
            return 'under_review'
        return 'pending'

    def get_status_display_info(self) -> dict:
        slug = self.get_status_slug()
        return STATUS_BADGES.get(slug, STATUS_BADGES['pending'])

    @property
    def status_definition(self):
        """Template/API compatibility — badge info without a DB row."""
        info = self.get_status_display_info()
        return SimpleNamespace(
            slug=self.get_status_slug(),
            label=info['label'],
            badge_class=info['badge_class'],
            icon=info['icon'],
        )

    @property
    def total_rubric_score(self):
        scores = self.rubric_scores_json or {}
        return sum(int(v) for v in scores.values())

    @property
    def is_certificate_eligible(self) -> bool:
        return (
            self.status == self.Status.APPROVED
            and self.teacher_approved
            and self.admin_approved
            and self.is_final_submission
        )

    def refresh_status_from_flags(self):
        if self.status == self.Status.REJECTED:
            return
        if self.teacher_approved and self.admin_approved:
            self.status = self.Status.APPROVED
            self.submission_round = self.SubmissionRound.FINAL
            self.is_locked = True
        else:
            self.status = self.Status.PENDING
            if self.submission_round == self.SubmissionRound.FINAL:
                self.submission_round = self.SubmissionRound.REVIEW


class ReportVersion(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='versions')
    file = models.FileField(upload_to=version_upload_path)
    version_number = models.PositiveIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version_number']
        unique_together = [['report', 'version_number']]

    def __str__(self):
        return f'{self.report.title} v{self.version_number}'


class Comment(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.user} on {self.report_id}'


class ReportRequest(models.Model):
    """Merged re-evaluation and deadline extension requests."""

    class RequestType(models.TextChoices):
        REEVALUATION = 'reevaluation', 'Re-evaluation'
        EXTENSION = 'extension', 'Extension'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='requests')
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='report_requests',
    )
    request_type = models.CharField(max_length=20, choices=RequestType.choices, db_index=True)
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    updated_marks = models.PositiveIntegerField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='report_request_reviews',
    )
    admin_note = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_request_type_display()} #{self.pk} — report {self.report_id}'


class ReEvaluationRequestManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(request_type=ReportRequest.RequestType.REEVALUATION)

    def create(self, **kwargs):
        kwargs['request_type'] = ReportRequest.RequestType.REEVALUATION
        return super().create(**kwargs)


class ReEvaluationRequest(ReportRequest):
    objects = ReEvaluationRequestManager()

    class Meta:
        proxy = True
        verbose_name = 'Re-evaluation request'


class DeadlineExtensionRequestManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(request_type=ReportRequest.RequestType.EXTENSION)

    def create(self, **kwargs):
        kwargs['request_type'] = ReportRequest.RequestType.EXTENSION
        return super().create(**kwargs)


class DeadlineExtensionRequest(ReportRequest):
    objects = DeadlineExtensionRequestManager()

    class Meta:
        proxy = True
        verbose_name = 'Deadline extension request'


class ActivityLog(models.Model):
    class Action(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted'
        RESUBMITTED = 'resubmitted', 'Resubmitted'
        TEACHER_APPROVED = 'teacher_approved', 'Teacher approved'
        TEACHER_REJECTED = 'teacher_rejected', 'Teacher rejected'
        ADMIN_APPROVED = 'admin_approved', 'Admin approved'
        ADMIN_REJECTED = 'admin_rejected', 'Admin rejected'
        DELETED = 'deleted', 'Deleted'
        RESTORED = 'restored', 'Restored'
        COMMENT = 'comment', 'Comment added'
        MARKS_SET = 'marks_set', 'Marks updated'
        REEVAL_REQUESTED = 'reeval_requested', 'Re-evaluation requested'
        REEVAL_RESOLVED = 'reeval_resolved', 'Re-evaluation resolved'
        LOGIN = 'login', 'Login'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='activity_logs',
    )
    action = models.CharField(max_length=40, choices=Action.choices)
    report = models.ForeignKey(
        Report,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs',
    )
    detail = models.CharField(max_length=500, blank=True)
    ip_address = models.CharField(max_length=45, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.action} by {self.user_id} @ {self.timestamp}'


class Notification(models.Model):
    """Personal alerts and role-targeted announcements."""

    class NotificationType(models.TextChoices):
        ALERT = 'alert', 'Alert'
        ANNOUNCEMENT = 'announcement', 'Announcement'

    class TargetRole(models.TextChoices):
        ALL = 'all', 'Everyone'
        ADMIN = 'admin', 'Admins'
        TEACHER = 'teacher', 'Teachers'
        STUDENT = 'student', 'Students'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True,
        help_text='Null for broadcast announcements.',
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.ALERT,
        db_index=True,
    )
    title = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    target_role = models.CharField(
        max_length=20,
        choices=TargetRole.choices,
        default=TargetRole.ALL,
    )
    is_read = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    link = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.notification_type}: {self.message[:50]}'


class AnnouncementManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(notification_type=Notification.NotificationType.ANNOUNCEMENT)

    def create(self, **kwargs):
        kwargs['notification_type'] = Notification.NotificationType.ANNOUNCEMENT
        kwargs.setdefault('user', None)
        return super().create(**kwargs)


class Announcement(Notification):
    objects = AnnouncementManager()

    class Meta:
        proxy = True
        verbose_name = 'Announcement'


class UserReportLink(models.Model):
    """Bookmarks and recent report views."""

    class LinkType(models.TextChoices):
        BOOKMARK = 'bookmark', 'Bookmark'
        RECENT_VIEW = 'recent_view', 'Recent view'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='report_links',
    )
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='user_links')
    link_type = models.CharField(max_length=20, choices=LinkType.choices, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    viewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [['user', 'report', 'link_type']]
        ordering = ['-viewed_at', '-created_at']

    def __str__(self):
        return f'{self.user} {self.link_type} {self.report_id}'


class ReportBookmarkManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(link_type=UserReportLink.LinkType.BOOKMARK)

    def get_or_create(self, defaults=None, **kwargs):
        kwargs['link_type'] = UserReportLink.LinkType.BOOKMARK
        defaults = defaults or {}
        defaults.setdefault('link_type', UserReportLink.LinkType.BOOKMARK)
        return super().get_or_create(defaults=defaults, **kwargs)


class ReportBookmark(UserReportLink):
    objects = ReportBookmarkManager()

    class Meta:
        proxy = True


class ReportRecentViewManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(link_type=UserReportLink.LinkType.RECENT_VIEW)

    def get_or_create(self, defaults=None, **kwargs):
        kwargs['link_type'] = UserReportLink.LinkType.RECENT_VIEW
        defaults = defaults or {}
        defaults.setdefault('link_type', UserReportLink.LinkType.RECENT_VIEW)
        defaults.setdefault('viewed_at', timezone.now())
        return super().get_or_create(defaults=defaults, **kwargs)


class ReportRecentView(UserReportLink):
    objects = ReportRecentViewManager()

    class Meta:
        proxy = True


class CertificateCelebrationAcknowledgment(models.Model):
    """Tracks when a student has seen the certificate achievement celebration."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='certificate_celebration_acks',
    )
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name='certificate_celebration_acks',
    )
    acknowledged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['user', 'report']]
        ordering = ['-acknowledged_at']

    def __str__(self):
        return f'{self.user_id} ack celebration for report {self.report_id}'
