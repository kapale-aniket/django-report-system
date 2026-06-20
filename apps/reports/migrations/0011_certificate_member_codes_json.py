from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0010_report_assigned_teacher'),
    ]

    operations = [
        migrations.AddField(
            model_name='report',
            name='certificate_member_codes_json',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Map of group member user id (str) to personal certificate verification codes.',
            ),
        ),
    ]
