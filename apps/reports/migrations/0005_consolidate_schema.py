# Consolidated schema: merge related tables, migrate existing rows, then drop legacy tables.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def migrate_consolidated_data(apps, schema_editor):
    Rubric = apps.get_model('reports', 'Rubric')
    RubricCriteria = apps.get_model('reports', 'RubricCriteria')
    ReportEvaluation = apps.get_model('reports', 'ReportEvaluation')
    Report = apps.get_model('reports', 'Report')
    ReEvaluationRequest = apps.get_model('reports', 'ReEvaluationRequest')
    DeadlineExtensionRequest = apps.get_model('reports', 'DeadlineExtensionRequest')
    ReportBookmark = apps.get_model('reports', 'ReportBookmark')
    ReportRecentView = apps.get_model('reports', 'ReportRecentView')
    LoginHistory = apps.get_model('reports', 'LoginHistory')
    ActivityLog = apps.get_model('reports', 'ActivityLog')
    Announcement = apps.get_model('reports', 'Announcement')
    Notification = apps.get_model('reports', 'Notification')
    ReportRequest = apps.get_model('reports', 'ReportRequest')
    UserReportLink = apps.get_model('reports', 'UserReportLink')

    for rubric in Rubric.objects.all():
        criteria = []
        for c in RubricCriteria.objects.filter(rubric_id=rubric.pk).order_by('sort_order', 'pk'):
            criteria.append(
                {
                    'id': c.pk,
                    'name': c.name,
                    'max_score': c.max_score,
                    'sort_order': c.sort_order,
                }
            )
        rubric.criteria_json = criteria
        rubric.save(update_fields=['criteria_json'])

    for report in Report.objects.all():
        scores = {}
        for ev in ReportEvaluation.objects.filter(report_id=report.pk):
            scores[str(ev.criterion_id)] = ev.score
        if scores:
            report.rubric_scores_json = scores
            report.save(update_fields=['rubric_scores_json'])

    for req in ReEvaluationRequest.objects.all():
        ReportRequest.objects.create(
            report_id=req.report_id,
            student_id=req.student_id,
            request_type='reevaluation',
            reason=req.reason,
            status=req.status,
            updated_marks=req.updated_marks,
            created_at=req.created_at,
            resolved_at=req.resolved_at,
        )

    for ext in DeadlineExtensionRequest.objects.all():
        ReportRequest.objects.create(
            report_id=ext.report_id,
            student_id=ext.student_id,
            request_type='extension',
            reason=ext.reason,
            status=ext.status,
            reviewed_by_id=getattr(ext, 'reviewed_by_id', None),
            admin_note=getattr(ext, 'admin_note', '') or '',
            created_at=ext.created_at,
            resolved_at=ext.resolved_at,
        )

    for bm in ReportBookmark.objects.all():
        UserReportLink.objects.create(
            user_id=bm.user_id,
            report_id=bm.report_id,
            link_type='bookmark',
            created_at=bm.created_at,
        )

    for rv in ReportRecentView.objects.all():
        UserReportLink.objects.create(
            user_id=rv.user_id,
            report_id=rv.report_id,
            link_type='recent_view',
            viewed_at=rv.viewed_at,
        )

    for lh in LoginHistory.objects.all():
        ActivityLog.objects.create(
            user_id=lh.user_id,
            action='login',
            ip_address=lh.ip_address or '',
            user_agent=lh.user_agent or '',
            timestamp=lh.created_at,
        )

    for ann in Announcement.objects.all():
        Notification.objects.create(
            user=None,
            notification_type='announcement',
            title=ann.title,
            message=ann.message,
            target_role=ann.target_role,
            is_active=ann.is_active,
            is_read=False,
            link='',
            created_at=ann.created_at,
            updated_at=ann.updated_at,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0004_certificate_verification_code'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='rubric',
            name='criteria_json',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='List of {id, name, max_score, sort_order} criterion definitions.',
            ),
        ),
        migrations.AddField(
            model_name='report',
            name='rubric_scores_json',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Map of criterion id (str) to score.',
            ),
        ),
        migrations.AddField(
            model_name='activitylog',
            name='ip_address',
            field=models.CharField(blank=True, max_length=45),
        ),
        migrations.AddField(
            model_name='activitylog',
            name='user_agent',
            field=models.CharField(blank=True, max_length=512),
        ),
        migrations.AlterField(
            model_name='activitylog',
            name='action',
            field=models.CharField(
                choices=[
                    ('submitted', 'Submitted'),
                    ('resubmitted', 'Resubmitted'),
                    ('teacher_approved', 'Teacher approved'),
                    ('teacher_rejected', 'Teacher rejected'),
                    ('admin_approved', 'Admin approved'),
                    ('admin_rejected', 'Admin rejected'),
                    ('deleted', 'Deleted'),
                    ('restored', 'Restored'),
                    ('comment', 'Comment added'),
                    ('marks_set', 'Marks updated'),
                    ('reeval_requested', 'Re-evaluation requested'),
                    ('reeval_resolved', 'Re-evaluation resolved'),
                    ('login', 'Login'),
                ],
                max_length=40,
            ),
        ),
        migrations.AddField(
            model_name='notification',
            name='notification_type',
            field=models.CharField(
                choices=[('alert', 'Alert'), ('announcement', 'Announcement')],
                db_index=True,
                default='alert',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='notification',
            name='title',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='notification',
            name='target_role',
            field=models.CharField(
                choices=[
                    ('all', 'Everyone'),
                    ('admin', 'Admins'),
                    ('teacher', 'Teachers'),
                    ('student', 'Students'),
                ],
                default='all',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='notification',
            name='is_active',
            field=models.BooleanField(db_index=True, default=True),
        ),
        migrations.AddField(
            model_name='notification',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='notification',
            name='user',
            field=models.ForeignKey(
                blank=True,
                help_text='Null for broadcast announcements.',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='notifications',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.CreateModel(
            name='ReportRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_type', models.CharField(
                    choices=[('reevaluation', 'Re-evaluation'), ('extension', 'Extension')],
                    db_index=True,
                    max_length=20,
                )),
                ('reason', models.TextField()),
                ('status', models.CharField(
                    choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')],
                    db_index=True,
                    default='pending',
                    max_length=20,
                )),
                ('updated_marks', models.PositiveIntegerField(blank=True, null=True)),
                ('admin_note', models.CharField(blank=True, max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('report', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='requests',
                    to='reports.report',
                )),
                ('reviewed_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='report_request_reviews',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('student', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='report_requests',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='UserReportLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('link_type', models.CharField(
                    choices=[('bookmark', 'Bookmark'), ('recent_view', 'Recent view')],
                    db_index=True,
                    max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('viewed_at', models.DateTimeField(blank=True, null=True)),
                ('report', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='user_links',
                    to='reports.report',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='report_links',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['-viewed_at', '-created_at']},
        ),
        migrations.AlterUniqueTogether(
            name='userreportlink',
            unique_together={('user', 'report', 'link_type')},
        ),
        migrations.RunPython(migrate_consolidated_data, migrations.RunPython.noop),
        migrations.RemoveField(model_name='report', name='status_definition'),
        migrations.DeleteModel(name='ReportEvaluation'),
        migrations.DeleteModel(name='RubricCriteria'),
        migrations.DeleteModel(name='ReportStatusDefinition'),
        migrations.DeleteModel(name='ReEvaluationRequest'),
        migrations.DeleteModel(name='DeadlineExtensionRequest'),
        migrations.DeleteModel(name='ReportBookmark'),
        migrations.DeleteModel(name='ReportRecentView'),
        migrations.DeleteModel(name='LoginHistory'),
        migrations.DeleteModel(name='Announcement'),
        migrations.CreateModel(
            name='ReEvaluationRequest',
            fields=[],
            options={
                'verbose_name': 'Re-evaluation request',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('reports.reportrequest',),
        ),
        migrations.CreateModel(
            name='DeadlineExtensionRequest',
            fields=[],
            options={
                'verbose_name': 'Deadline extension request',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('reports.reportrequest',),
        ),
        migrations.CreateModel(
            name='ReportBookmark',
            fields=[],
            options={'proxy': True, 'indexes': [], 'constraints': []},
            bases=('reports.userreportlink',),
        ),
        migrations.CreateModel(
            name='ReportRecentView',
            fields=[],
            options={'proxy': True, 'indexes': [], 'constraints': []},
            bases=('reports.userreportlink',),
        ),
        migrations.CreateModel(
            name='Announcement',
            fields=[],
            options={'verbose_name': 'Announcement', 'proxy': True, 'indexes': [], 'constraints': []},
            bases=('reports.notification',),
        ),
    ]
