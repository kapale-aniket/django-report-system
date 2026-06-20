from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def populate_group_metadata(apps, schema_editor):
    ProjectGroup = apps.get_model('reports', 'ProjectGroup')
    User = apps.get_model('accounts', 'User')
    for group in ProjectGroup.objects.all().iterator():
        members = list(group.members.order_by('pk').values_list('pk', flat=True))
        if not members:
            continue
        first_member = User.objects.filter(pk=members[0]).first()
        if not first_member:
            continue
        updates = {}
        if not group.department:
            updates['department'] = (getattr(first_member, 'department', None) or '').strip()
        if not group.creator_id:
            updates['creator_id'] = first_member.pk
        if updates:
            ProjectGroup.objects.filter(pk=group.pk).update(**updates)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('reports', '0011_certificate_member_codes_json'),
    ]

    operations = [
        migrations.AddField(
            model_name='projectgroup',
            name='assigned_teacher',
            field=models.ForeignKey(
                blank=True,
                help_text='Faculty guide for this group — assigned by admin based on department.',
                limit_choices_to={'role': 'teacher'},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='assigned_project_groups',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='projectgroup',
            name='creator',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='created_project_groups',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='projectgroup',
            name='department',
            field=models.CharField(blank=True, db_index=True, max_length=120),
        ),
        migrations.AddField(
            model_name='projectgroup',
            name='description',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='projectgroup',
            name='is_public',
            field=models.BooleanField(
                db_index=True,
                default=True,
                help_text='Public groups are visible to all students after creation.',
            ),
        ),
        migrations.AlterModelOptions(
            name='projectgroup',
            options={'ordering': ['-created_at', 'name']},
        ),
        migrations.RunPython(populate_group_metadata, migrations.RunPython.noop),
    ]
