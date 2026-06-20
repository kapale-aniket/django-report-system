"""Department choices for forms — backed by Department model."""

from apps.accounts.infrastructure.models import Department

ADD_DEPARTMENT_VALUE = '__add_department__'
ADD_DEPARTMENT_LABEL = '+ Add department…'

DEFAULT_DEPARTMENTS = (
    'Administration',
    'Civil Engineering',
    'Computer Science',
    'Electronics & Communication',
    'Information Technology',
    'Mechanical Engineering',
)


def get_department_names(*, extra=()) -> list[str]:
    """Return sorted active department names."""
    names = set(DEFAULT_DEPARTMENTS)
    names.update(Department.objects.filter(is_active=True).values_list('name', flat=True))

    from apps.accounts.models import User

    for dept_name in User.objects.exclude(department='').exclude(department__isnull=True).values_list('department', flat=True):
        cleaned = (dept_name or '').strip()
        if cleaned:
            names.add(cleaned)

    for item in extra or ():
        if item and str(item).strip() and item != ADD_DEPARTMENT_VALUE:
            names.add(str(item).strip())

    return sorted(names, key=str.casefold)


def get_department_choices(blank_label='Select department…', extra=(), include_add_option=False):
    """Return sorted (value, label) pairs for department dropdowns."""
    choices = [('', blank_label)]
    choices.extend((name, name) for name in get_department_names(extra=extra))
    if include_add_option:
        choices.append((ADD_DEPARTMENT_VALUE, ADD_DEPARTMENT_LABEL))
    return choices
