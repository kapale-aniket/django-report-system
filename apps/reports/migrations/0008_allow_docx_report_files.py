import django.core.validators
from django.db import migrations, models

import apps.reports.infrastructure.models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0007_report_is_final_submission'),
    ]

    operations = [
        migrations.AlterField(
            model_name='report',
            name='extracted_text',
            field=models.TextField(
                blank=True,
                default='',
                help_text='Native text extracted from the submitted report file.',
            ),
        ),
        migrations.AlterField(
            model_name='report',
            name='file',
            field=models.FileField(
                upload_to=apps.reports.infrastructure.models.report_upload_path,
                validators=[
                    django.core.validators.FileExtensionValidator(
                        allowed_extensions=['pdf', 'docx']
                    )
                ],
            ),
        ),
    ]
