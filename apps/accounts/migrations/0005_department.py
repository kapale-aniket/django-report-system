from django.db import migrations, models

DEFAULT_DEPARTMENTS = (
    'Administration',
    'Civil Engineering',
    'Computer Science',
    'Electronics & Communication',
    'Information Technology',
    'Mechanical Engineering',
)


def seed_departments(apps, schema_editor):
    Department = apps.get_model('accounts', 'Department')
    User = apps.get_model('accounts', 'User')

    names = set(DEFAULT_DEPARTMENTS)
    for dept_name in User.objects.exclude(department='').exclude(department__isnull=True).values_list('department', flat=True):
        cleaned = (dept_name or '').strip()
        if cleaned:
            names.add(cleaned)

    for name in sorted(names, key=str.casefold):
        Department.objects.get_or_create(name=name, defaults={'is_active': True})


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_user_profile_photo'),
    ]

    operations = [
        migrations.CreateModel(
            name='Department',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120, unique=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.RunPython(seed_departments, migrations.RunPython.noop),
    ]
