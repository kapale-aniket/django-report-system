# Consolidated QA schema: single qa_item table with proxy models.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def migrate_qa_data(apps, schema_editor):
    FAQ = apps.get_model('qa', 'FAQ')
    UserQuestion = apps.get_model('qa', 'UserQuestion')
    VisitorQuestion = apps.get_model('qa', 'VisitorQuestion')
    QAItem = apps.get_model('qa', 'QAItem')

    for faq in FAQ.objects.all():
        QAItem.objects.create(
            qa_type='faq',
            question=faq.question,
            answer_text=faq.answer,
            sort_order=faq.sort_order,
            is_active=faq.is_active,
            updated_at=faq.updated_at,
            status='answered',
        )

    for q in UserQuestion.objects.all():
        QAItem.objects.create(
            qa_type='user',
            user_id=q.user_id,
            subject=q.subject,
            body=q.body,
            status=q.status,
            answer_text=q.answer_text,
            answered_at=q.answered_at,
            answered_by_id=q.answered_by_id,
            created_at=q.created_at,
            updated_at=q.created_at,
        )

    for v in VisitorQuestion.objects.all():
        QAItem.objects.create(
            qa_type='visitor',
            name=v.name,
            email=v.email,
            subject=v.subject,
            body=v.body,
            status=v.status,
            answer_text=v.answer_text,
            answered_at=v.answered_at,
            answered_by_id=v.answered_by_id,
            created_at=v.created_at,
            updated_at=v.created_at,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('qa', '0002_visitor_question'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='QAItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('qa_type', models.CharField(
                    choices=[('faq', 'FAQ'), ('user', 'User question'), ('visitor', 'Visitor question')],
                    db_index=True,
                    max_length=20,
                )),
                ('name', models.CharField(blank=True, max_length=120)),
                ('email', models.EmailField(blank=True, default='', max_length=254)),
                ('subject', models.CharField(blank=True, max_length=200)),
                ('question', models.CharField(blank=True, help_text='FAQ question text.', max_length=500)),
                ('body', models.TextField(blank=True, help_text='User/visitor question body.')),
                ('answer_text', models.TextField(blank=True)),
                ('status', models.CharField(
                    choices=[('open', 'Open'), ('answered', 'Answered')],
                    db_index=True,
                    default='open',
                    max_length=20,
                )),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('answered_at', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('answered_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='qa_replies_given',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('user', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='qa_items',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.RunPython(migrate_qa_data, migrations.RunPython.noop),
        migrations.DeleteModel(name='FAQ'),
        migrations.DeleteModel(name='UserQuestion'),
        migrations.DeleteModel(name='VisitorQuestion'),
        migrations.CreateModel(
            name='FAQ',
            fields=[],
            options={
                'verbose_name': 'FAQ',
                'verbose_name_plural': 'FAQs',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('qa.qaitem',),
        ),
        migrations.CreateModel(
            name='UserQuestion',
            fields=[],
            options={'proxy': True, 'indexes': [], 'constraints': []},
            bases=('qa.qaitem',),
        ),
        migrations.CreateModel(
            name='VisitorQuestion',
            fields=[],
            options={'proxy': True, 'indexes': [], 'constraints': []},
            bases=('qa.qaitem',),
        ),
    ]
