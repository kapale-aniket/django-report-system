from __future__ import annotations

from rest_framework import serializers

from apps.reports.infrastructure.models import (
    ActivityLog,
    Comment,
    DeadlineExtensionRequest,
    Notification,
    ReEvaluationRequest,
    Report,
    ReportVersion,
    SystemSettings,
)


class ReportListSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(source='student.username', read_only=True)
    student_name = serializers.SerializerMethodField()
    department = serializers.CharField(source='student.department', read_only=True)
    status_label = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = (
            'id',
            'title',
            'student_username',
            'student_name',
            'department',
            'status',
            'status_label',
            'marks',
            'teacher_marks',
            'teacher_approved',
            'admin_approved',
            'is_late_submission',
            'is_pinned',
            'is_deleted',
            'is_archived',
            'academic_year',
            'submitted_at',
            'updated_at',
        )

    def get_student_name(self, obj) -> str:
        return obj.student.get_full_name() or obj.student.username

    def get_status_label(self, obj) -> str:
        return obj.get_status_display_info()['label']


class ReportVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportVersion
        fields = ('id', 'version_number', 'file', 'uploaded_at')


class CommentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.SerializerMethodField()
    author_role = serializers.CharField(source='user.role', read_only=True)
    role_label = serializers.CharField(source='user.get_role_display', read_only=True)

    class Meta:
        model = Comment
        fields = ('id', 'username', 'full_name', 'author_role', 'role_label', 'message', 'created_at')

    def get_full_name(self, obj) -> str:
        return obj.user.get_full_name() or obj.user.username


class ActivityLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True, default='')
    report_title = serializers.CharField(source='report.title', read_only=True, default='')

    class Meta:
        model = ActivityLog
        fields = ('id', 'username', 'action', 'report', 'report_title', 'detail', 'timestamp')


class RubricRowSerializer(serializers.Serializer):
    criterion_id = serializers.IntegerField()
    criterion_name = serializers.CharField()
    score = serializers.IntegerField()
    max_score = serializers.IntegerField()


class ReEvaluationRequestSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(source='student.username', read_only=True)

    class Meta:
        model = ReEvaluationRequest
        fields = (
            'id',
            'report',
            'student',
            'student_username',
            'reason',
            'status',
            'updated_marks',
            'created_at',
            'resolved_at',
        )
        read_only_fields = ('id', 'report', 'student', 'status', 'updated_marks', 'created_at', 'resolved_at')


class ExtensionRequestSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(source='student.username', read_only=True)
    report_title = serializers.CharField(source='report.title', read_only=True)

    class Meta:
        model = DeadlineExtensionRequest
        fields = (
            'id',
            'report',
            'report_title',
            'student',
            'student_username',
            'reason',
            'status',
            'admin_note',
            'created_at',
            'resolved_at',
        )
        read_only_fields = fields


class ReportDetailSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(source='student.username', read_only=True)
    student_name = serializers.SerializerMethodField()
    department = serializers.CharField(source='student.department', read_only=True)
    assigned_teacher = serializers.SerializerMethodField()
    assigned_teacher_id = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()
    comments = CommentSerializer(many=True, read_only=True)
    versions = ReportVersionSerializer(many=True, read_only=True)
    timeline = ActivityLogSerializer(many=True, read_only=True, source='activity_logs')
    rubric_rows = RubricRowSerializer(many=True, read_only=True)
    bookmarked = serializers.BooleanField(read_only=True)
    can_comment = serializers.BooleanField(read_only=True)
    can_resubmit = serializers.BooleanField(read_only=True)
    pending_reeval = ReEvaluationRequestSerializer(read_only=True, allow_null=True)
    pending_extension = ExtensionRequestSerializer(read_only=True, allow_null=True)
    reeval_admin_queue = ReEvaluationRequestSerializer(many=True, read_only=True)

    class Meta:
        model = Report
        fields = (
            'id',
            'title',
            'student',
            'student_username',
            'student_name',
            'department',
            'assigned_teacher',
            'assigned_teacher_id',
            'file',
            'status',
            'status_label',
            'teacher_approved',
            'admin_approved',
            'rejection_reason',
            'is_late_submission',
            'certificate_generated',
            'is_final_submission',
            'marks',
            'teacher_marks',
            'feedback',
            'submission_round',
            'is_locked',
            'attempt_count',
            'is_deleted',
            'tags',
            'group',
            'rubric',
            'is_pinned',
            'academic_year',
            'is_archived',
            'submitted_at',
            'updated_at',
            'comments',
            'versions',
            'timeline',
            'rubric_rows',
            'bookmarked',
            'can_comment',
            'can_resubmit',
            'pending_reeval',
            'pending_extension',
            'reeval_admin_queue',
        )

    def get_student_name(self, obj) -> str:
        return obj.student.get_full_name() or obj.student.username

    def get_assigned_teacher(self, obj) -> str:
        from apps.reports.teacher_helpers import get_report_assigned_teacher

        teacher = get_report_assigned_teacher(obj)
        if not teacher:
            return ''
        return teacher.get_full_name() or teacher.username

    def get_assigned_teacher_id(self, obj):
        from apps.reports.teacher_helpers import get_report_assigned_teacher_id

        return get_report_assigned_teacher_id(obj)

    def get_status_label(self, obj) -> str:
        return obj.get_status_display_info()['label']


class ReportAssignTeacherSerializer(serializers.Serializer):
    teacher_id = serializers.IntegerField(required=False, allow_null=True)


class ReportSubmitSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    file = serializers.FileField()
    tags = serializers.CharField(required=False, allow_blank=True, default='')
    submission_type = serializers.ChoiceField(
        choices=[('individual', 'Individual project'), ('group', 'Group project')],
        default='individual',
    )
    project_group_id = serializers.IntegerField(required=False, allow_null=True)
    academic_year = serializers.CharField(max_length=16)

    def validate(self, attrs):
        from application.services.project_group_service import ProjectGroupService
        from core.exceptions.base import BusinessLogicError, NotFoundAppError, PermissionAppError, ValidationAppError

        submission_type = attrs.get('submission_type', 'individual')
        if submission_type == 'group':
            group_id = attrs.get('project_group_id')
            if not group_id:
                raise serializers.ValidationError({'project_group_id': 'Select a project group for a group submission.'})
            request = self.context.get('request')
            user = getattr(request, 'user', None)
            try:
                ProjectGroupService().resolve_group_for_submit(user, int(group_id))
            except ValidationAppError as exc:
                raise serializers.ValidationError({'project_group_id': str(exc)}) from exc
            except BusinessLogicError as exc:
                raise serializers.ValidationError({'project_group_id': str(exc)}) from exc
            except NotFoundAppError as exc:
                raise serializers.ValidationError({'project_group_id': str(exc)}) from exc
            except PermissionAppError as exc:
                raise serializers.ValidationError({'project_group_id': str(exc)}) from exc
        return attrs


class ReportResubmitSerializer(serializers.Serializer):
    file = serializers.FileField()


class TeacherApproveSerializer(serializers.Serializer):
    teacher_marks = serializers.IntegerField(required=False, min_value=0, max_value=100, allow_null=True)
    feedback = serializers.CharField(required=False, allow_blank=True, default='')
    is_final_submission = serializers.BooleanField(required=False, default=False)
    criterion_scores = serializers.DictField(
        child=serializers.IntegerField(min_value=0),
        required=False,
        default=dict,
    )


class RejectSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=2000)


class AdminApproveSerializer(serializers.Serializer):
    marks = serializers.IntegerField(min_value=0, max_value=100)


class CommentCreateSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=5000)


class BulkActionSerializer(serializers.Serializer):
    report_ids = serializers.ListField(child=serializers.IntegerField(), min_length=1)
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    reason = serializers.CharField(required=False, allow_blank=True, default='')


class ReEvaluationCreateSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=5000)


class ReEvaluationResolveSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    updated_marks = serializers.IntegerField(required=False, min_value=0, max_value=100)


class ExtensionCreateSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=5000)


class ExtensionResolveSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=['approve', 'reject'])
    note = serializers.CharField(required=False, allow_blank=True, max_length=500, default='')


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ('id', 'message', 'is_read', 'link', 'created_at')


class SystemSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSettings
        fields = (
            'submission_deadline',
            'max_attempts',
            'max_file_size_mb',
            'group_submission_deadline',
            'group_max_attempts',
            'group_min_members',
            'group_max_members',
            'updated_at',
        )
        read_only_fields = ('updated_at',)

    def validate(self, attrs):
        min_members = attrs.get('group_min_members')
        max_members = attrs.get('group_max_members')
        if min_members is None and self.instance is not None:
            min_members = self.instance.group_min_members
        if max_members is None and self.instance is not None:
            max_members = self.instance.group_max_members
        if min_members and max_members and min_members > max_members:
            raise serializers.ValidationError(
                {'group_max_members': 'Minimum group members cannot exceed maximum group members.'}
            )
        return attrs


class LeaderboardReportSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(source='student.username', read_only=True)
    student_name = serializers.SerializerMethodField()
    department = serializers.CharField(source='student.department', read_only=True)

    class Meta:
        model = Report
        fields = ('id', 'title', 'student_username', 'student_name', 'department', 'marks', 'submitted_at')

    def get_student_name(self, obj) -> str:
        return obj.student.get_full_name() or obj.student.username


class TopStudentSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    full_name = serializers.CharField()
    department = serializers.CharField()
    avg_marks = serializers.FloatField()


class DepartmentRankingSerializer(serializers.Serializer):
    department = serializers.CharField()
    avg_marks = serializers.FloatField()
    report_count = serializers.IntegerField()


class AnalyticsSerializer(serializers.Serializer):
    total_students = serializers.IntegerField()
    total_teachers = serializers.IntegerField()
    total_reports = serializers.IntegerField()
    pending_reports = serializers.IntegerField()
    approved_reports = serializers.IntegerField()
    rejected_reports = serializers.IntegerField()
    approval_rate_pct = serializers.FloatField()
    late_pct = serializers.FloatField()
    chart_labels = serializers.ListField(child=serializers.CharField())
    chart_submissions = serializers.ListField(child=serializers.IntegerField())
    chart_approved = serializers.ListField(child=serializers.IntegerField())
    chart_pending = serializers.ListField(child=serializers.IntegerField())
    submission_deadline = serializers.DateTimeField()
    max_attempts = serializers.IntegerField()
    max_file_size_mb = serializers.IntegerField()


class TeacherWorkloadSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    done = serializers.IntegerField()
    pending_review = serializers.IntegerField()
    awaiting_admin = serializers.IntegerField()


class SubmissionTrackingSerializer(serializers.Serializer):
    submitted_count = serializers.IntegerField()
    pending_count = serializers.IntegerField()
    submitted = serializers.ListField()
    pending = serializers.ListField()
