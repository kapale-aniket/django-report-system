import django_filters

from apps.reports.infrastructure.models import Report


class ReportFilterSet(django_filters.FilterSet):
    """Django-filter FilterSet for report list endpoints."""

    search = django_filters.CharFilter(method='filter_search')
    status = django_filters.CharFilter(method='filter_status')
    department = django_filters.CharFilter(field_name='student__department', lookup_expr='icontains')
    min_marks = django_filters.NumberFilter(field_name='marks', lookup_expr='gte')
    max_marks = django_filters.NumberFilter(field_name='marks', lookup_expr='lte')
    date_from = django_filters.DateFilter(field_name='submitted_at', lookup_expr='date__gte')
    date_to = django_filters.DateFilter(field_name='submitted_at', lookup_expr='date__lte')
    academic_year = django_filters.CharFilter(field_name='academic_year', lookup_expr='icontains')
    include_deleted = django_filters.BooleanFilter(field_name='is_deleted', method='filter_include_deleted')
    include_archived = django_filters.BooleanFilter(field_name='is_archived', method='filter_include_archived')

    class Meta:
        model = Report
        fields = [
            'search',
            'status',
            'department',
            'min_marks',
            'max_marks',
            'date_from',
            'date_to',
            'academic_year',
            'include_deleted',
            'include_archived',
        ]

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        from django.db.models import Q

        return queryset.filter(
            Q(title__icontains=value)
            | Q(student__username__icontains=value)
            | Q(student__first_name__icontains=value)
            | Q(student__last_name__icontains=value)
            | Q(tags__icontains=value)
        )

    def filter_status(self, queryset, name, value):
        if not value:
            return queryset
        if value == Report.Status.PENDING:
            return queryset.filter(status=Report.Status.PENDING)
        if value == Report.Status.APPROVED:
            return queryset.filter(status=Report.Status.APPROVED)
        if value == Report.Status.REJECTED:
            return queryset.filter(status=Report.Status.REJECTED)
        if value == 'awaiting_admin':
            return queryset.filter(
                teacher_approved=True,
                admin_approved=False,
                status=Report.Status.PENDING,
            )
        return queryset.filter(status=value)

    def filter_include_deleted(self, queryset, name, value):
        if value:
            return queryset
        return queryset.filter(is_deleted=False)

    def filter_include_archived(self, queryset, name, value):
        if value:
            return queryset
        return queryset.filter(is_archived=False)
