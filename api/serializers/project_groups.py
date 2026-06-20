from __future__ import annotations

from rest_framework import serializers

from apps.reports.infrastructure.models import ProjectGroup


class ProjectGroupMemberSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    full_name = serializers.CharField()


class ProjectGroupSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    has_active_submission = serializers.SerializerMethodField()
    assigned_teacher_name = serializers.SerializerMethodField()
    creator_name = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()

    class Meta:
        model = ProjectGroup
        fields = (
            'id',
            'name',
            'description',
            'department',
            'is_public',
            'member_count',
            'has_active_submission',
            'assigned_teacher',
            'assigned_teacher_name',
            'creator',
            'creator_name',
            'members',
            'created_at',
        )

    def get_member_count(self, obj) -> int:
        annotated = getattr(obj, 'member_total', None)
        if annotated is not None:
            return int(annotated)
        return obj.member_count

    def get_has_active_submission(self, obj) -> bool:
        return obj.has_active_submission

    def get_assigned_teacher_name(self, obj) -> str:
        teacher = getattr(obj, 'assigned_teacher', None)
        if not teacher:
            return ''
        return teacher.get_full_name() or teacher.username

    def get_creator_name(self, obj) -> str:
        creator = getattr(obj, 'creator', None)
        if not creator:
            return ''
        return creator.get_full_name() or creator.username

    def get_members(self, obj):
        members = getattr(obj, '_prefetched_objects_cache', {}).get('members')
        if members is None:
            members = obj.members.all()
        return [
            {
                'id': member.pk,
                'username': member.username,
                'full_name': member.get_full_name() or member.username,
            }
            for member in members
        ]


class ProjectGroupCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    project_mate_ids = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, attrs):
        from apps.reports.group_helpers import parse_mate_ids, validate_project_mates
        from core.exceptions.base import ValidationAppError

        request = self.context.get('request')
        user = getattr(request, 'user', None)
        mate_ids = parse_mate_ids(attrs.get('project_mate_ids'))
        try:
            validate_project_mates(user, mate_ids)
        except ValidationAppError as exc:
            raise serializers.ValidationError({'project_mate_ids': str(exc)}) from exc
        attrs['project_mate_ids_list'] = mate_ids
        return attrs


class ProjectGroupAssignTeacherSerializer(serializers.Serializer):
    teacher_id = serializers.IntegerField(required=False, allow_null=True)
