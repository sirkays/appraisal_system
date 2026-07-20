# Generated manually for appraisal cycle archival lifecycle.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appraisals', '0009_form_field_system'),
    ]

    operations = [
        migrations.AddField(
            model_name='appraisalcycle',
            name='archived_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='appraisalcycle',
            name='status',
            field=models.CharField(
                choices=[
                    ('DRAFT', 'Draft'),
                    ('ACTIVE', 'Active'),
                    ('CLOSED', 'Closed'),
                    ('ARCHIVED', 'Archived'),
                ],
                default='DRAFT',
                max_length=20,
            ),
        ),
    ]
