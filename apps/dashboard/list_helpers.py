"""Shared list/table pagination and sorting for template views."""
from __future__ import annotations

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

TABLE_PAGE_SIZE = 10


def get_filter_querystring(request, *, exclude: tuple[str, ...] = ('page',)) -> str:
    params = request.GET.copy()
    for key in exclude:
        params.pop(key, None)
    return params.urlencode()


def apply_sort(
    queryset,
    request,
    *,
    allowed: dict[str, str],
    default_field: str = 'pk',
    default_dir: str = 'asc',
):
    """
    Sort queryset using GET sort_by + sort_dir.
    `allowed` maps query param value -> ORM field name.
    """
    sort_by = (request.GET.get('sort_by') or default_field).strip()
    sort_dir = (request.GET.get('sort_dir') or default_dir).strip().lower()
    field = allowed.get(sort_by, allowed.get(default_field, default_field))
    if sort_dir == 'desc':
        field = f'-{field.lstrip("-")}'
    else:
        field = field.lstrip('-')
    return queryset.order_by(field)


def paginate_table(request, queryset, *, per_page: int = TABLE_PAGE_SIZE):
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')
    try:
        page = paginator.page(page_number)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)
    return page, get_filter_querystring(request)
