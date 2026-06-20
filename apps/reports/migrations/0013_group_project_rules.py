from django.conf import settings
from django.db import migrations, models


def copy_deadline_to_group(apps, schema_editor):
    SystemSettings = apps.get_model('reports', 'SystemSettings')
    for row in SystemSettings.objects.all().iterator():
        if not row.group_submission_deadline:
            row.group_submission_deadline = row.submission_deadline
            row.save(update_fields=['group_submission_deadline'])


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0012_project_group_workflow'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemsettings',
            name='group_max_attempts',
            field=models.PositiveIntegerField(
                default=5,
                help_text='Max resubmission attempts for group projects.',
            ),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='group_max_members',
            field=models.PositiveIntegerField(
                default=6,
                help_text='Maximum members in a project group (including the creator).',
            ),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='group_min_members',
            field=models.PositiveIntegerField(
                default=2,
                help_text='Minimum members in a project group (including the creator).',
            ),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='group_submission_deadline',
            field=models.DateTimeField(
                blank=True,
                help_text='Group project deadline. Falls back to the individual deadline when empty.',
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='systemsettings',
            name='max_attempts',
            field=models.PositiveIntegerField(
                default=5,
                help_text='Max resubmission attempts for individual projects.',
            ),
        ),
        migrations.AlterField(
            model_name='systemsettings',
            name='submission_deadline',
            field=models.DateTimeField(
                help_text='Individual project submissions after this instant are marked late.',
            ),
        ),
        migrations.RunPython(copy_deadline_to_group, migrations.RunPython.noop),
    ]
