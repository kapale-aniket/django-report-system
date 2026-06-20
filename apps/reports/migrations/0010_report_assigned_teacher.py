from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_report_teachers(apps, schema_editor):
    Report = apps.get_model('reports', 'Report')
    User = apps.get_model('accounts', 'User')
    for report in Report.objects.filter(assigned_teacher__isnull=True).iterator():
        student = User.objects.filter(pk=report.student_id).first()
        if student and student.assigned_teacher_id:
            Report.objects.filter(pk=report.pk).update(assigned_teacher_id=student.assigned_teacher_id)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('reports', '0009_certificate_template'),
    ]

    operations = [
        migrations.AddField(
            model_name='report',
            name='assigned_teacher',
            field=models.ForeignKey(
                blank=True,
                help_text='Faculty guide for this project. Each report can have a different teacher.',
                limit_choices_to={'role': 'teacher'},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='assigned_reports',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(backfill_report_teachers, migrations.RunPython.noop),
    ]
