from django.conf import settings
from django.db import migrations, models
import django.core.validators
import apps.reports.infrastructure.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('reports', '0008_allow_docx_report_files'),
    ]

    operations = [
        migrations.CreateModel(
            name='CertificateTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='Official certificate', max_length=200)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                (
                    'reference_image',
                    models.ImageField(
                        blank=True,
                        help_text='Upload a certificate design reference (PNG/JPG). Colors and background are derived from it.',
                        null=True,
                        upload_to=apps.reports.infrastructure.models.certificate_template_upload_path,
                        validators=[
                            django.core.validators.FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])
                        ],
                    ),
                ),
                ('title_text', models.CharField(default='Certificate of Completion', max_length=120)),
                ('subtitle_text', models.CharField(default='This is to certify that', max_length=200)),
                (
                    'footer_text',
                    models.CharField(
                        default='Approved by faculty and administration · Final submission verified',
                        max_length=220,
                    ),
                ),
                ('accent_color', models.CharField(default='#2d5a47', max_length=7)),
                ('secondary_color', models.CharField(default='#c9a227', max_length=7)),
                ('text_color', models.CharField(default='#2c2c2c', max_length=7)),
                ('muted_color', models.CharField(default='#5c5c5c', max_length=7)),
                ('background_color', models.CharField(default='#faf6ee', max_length=7)),
                (
                    'use_reference_background',
                    models.BooleanField(
                        default=True,
                        help_text='When enabled, the reference image fills the certificate background.',
                    ),
                ),
                ('style_json', models.JSONField(blank=True, default=dict)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'updated_by',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name='certificate_templates_updated',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'ordering': ['-updated_at'],
            },
        ),
    ]
