from __future__ import annotations

from rest_framework.permissions import IsAuthenticated

from api.base.base_api_view import BaseAPIView
from api.serializers.project_groups import (
    ProjectGroupAssignTeacherSerializer,
    ProjectGroupCreateSerializer,
    ProjectGroupSerializer,
)
from application.services.project_group_service import ProjectGroupService
from core.permissions import IsAdmin, IsStudent


def _service() -> ProjectGroupService:
    return ProjectGroupService()


class ProjectGroupListAPIView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        service = _service()
        department = (request.query_params.get('department') or '').strip()
        groups = service.list_public_groups(request.user, department=department)
        return self.success(
            ProjectGroupSerializer(groups, many=True).data,
            message='Project groups retrieved successfully',
        )


class ProjectGroupMyAPIView(BaseAPIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):
        groups = _service().list_my_groups(request.user)
        return self.success(
            ProjectGroupSerializer(groups, many=True).data,
            message='Your project groups retrieved successfully',
        )


class ProjectGroupSubmittableAPIView(BaseAPIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):
        groups = _service().submittable_groups_for_user(request.user)
        return self.success(
            ProjectGroupSerializer(groups, many=True).data,
            message='Submittable project groups retrieved successfully',
        )


class ProjectGroupCreateAPIView(BaseAPIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def post(self, request):
        serializer = ProjectGroupCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        group = self.run_service(
            lambda: _service().create_group(request.user, serializer.validated_data),
            action='create_project_group',
            user=request.user,
        )
        return self.success(
            ProjectGroupSerializer(group).data,
            message='Project group created successfully',
            status_code=201,
        )


class ProjectGroupDetailAPIView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        group = self.run_service(
            lambda: _service().get_group(request.user, pk),
            action='project_group_detail',
            user=request.user,
        )
        return self.success(
            ProjectGroupSerializer(group).data,
            message='Project group retrieved successfully',
        )


class ProjectGroupAdminListAPIView(BaseAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        department = (request.query_params.get('department') or '').strip()
        groups = _service().list_groups_for_admin(request.user, department=department)
        return self.success(
            ProjectGroupSerializer(groups, many=True).data,
            message='Project groups retrieved successfully',
        )


class ProjectGroupAssignTeacherAPIView(BaseAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        serializer = ProjectGroupAssignTeacherSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group = self.run_service(
            lambda: _service().assign_teacher(
                request.user,
                pk,
                serializer.validated_data.get('teacher_id'),
            ),
            action='assign_project_group_teacher',
            user=request.user,
        )
        return self.success(
            ProjectGroupSerializer(group).data,
            message='Group teacher assigned successfully',
        )
