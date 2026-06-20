from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0006_add_ai_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='report',
            name='is_final_submission',
            field=models.BooleanField(
                default=False,
                help_text='When checked by the teacher, a completion certificate is issued after admin approval.',
            ),
        ),
    ]
