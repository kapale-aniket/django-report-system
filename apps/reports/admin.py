from django.contrib import admin

from .models import (
    ActivityLog,
    Announcement,
    CertificateTemplate,
    Comment,
    DeadlineExtensionRequest,
    Notification,
    ProjectGroup,
    ReEvaluationRequest,
    Report,
    ReportBookmark,
    ReportRecentView,
    ReportRequest,
    ReportVersion,
    Rubric,
    SystemSettings,
    UserReportLink,
)


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = (
        'submission_deadline',
        'group_submission_deadline',
        'max_attempts',
        'group_max_attempts',
        'group_min_members',
        'group_max_members',
        'max_file_size_mb',
        'updated_at',
    )


@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'title_text', 'updated_at', 'updated_by')
    list_filter = ('is_active',)
    readonly_fields = ('updated_at', 'style_json')


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'student',
        'status',
        'marks',
        'teacher_approved',
        'admin_approved',
        'is_pinned',
        'academic_year',
        'is_archived',
        'submitted_at',
    )
    list_filter = (
        'status',
        'teacher_approved',
        'admin_approved',
        'is_late_submission',
        'submission_round',
        'is_deleted',
        'is_locked',
        'is_pinned',
        'is_archived',
    )
    search_fields = ('title', 'student__username', 'tags', 'academic_year')


@admin.register(ReportVersion)
class ReportVersionAdmin(admin.ModelAdmin):
    list_display = ('report', 'version_number', 'uploaded_at')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('report', 'user', 'created_at')


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'action', 'user', 'report', 'ip_address')
    list_filter = ('action',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('notification_type', 'user', 'title', 'message', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'is_active')


@admin.register(ReportRequest)
class ReportRequestAdmin(admin.ModelAdmin):
    list_display = ('request_type', 'report', 'student', 'status', 'created_at')
    list_filter = ('request_type', 'status')


@admin.register(ReEvaluationRequest)
class ReEvaluationRequestAdmin(admin.ModelAdmin):
    list_display = ('report', 'student', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(DeadlineExtensionRequest)
class DeadlineExtensionRequestAdmin(admin.ModelAdmin):
    list_display = ('report', 'student', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(UserReportLink)
class UserReportLinkAdmin(admin.ModelAdmin):
    list_display = ('user', 'report', 'link_type', 'created_at', 'viewed_at')
    list_filter = ('link_type',)


@admin.register(ReportBookmark)
class ReportBookmarkAdmin(admin.ModelAdmin):
    list_display = ('user', 'report', 'created_at')


@admin.register(ReportRecentView)
class ReportRecentViewAdmin(admin.ModelAdmin):
    list_display = ('user', 'report', 'viewed_at')


@admin.register(ProjectGroup)
class ProjectGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'assigned_teacher', 'is_public', 'created_at')
    list_filter = ('department', 'is_public')
    search_fields = ('name', 'department')
    filter_horizontal = ('members',)


@admin.register(Rubric)
class RubricAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_default', 'is_active')


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'target_role', 'is_active', 'created_at')
    list_filter = ('target_role', 'is_active')
