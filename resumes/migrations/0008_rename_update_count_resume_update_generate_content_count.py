# Generated by Django 5.1.3 on 2025-03-21 14:12

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('resumes', '0007_resume_update_count'),
    ]

    operations = [
        migrations.RenameField(
            model_name='resume',
            old_name='update_count',
            new_name='update_generate_content_count',
        ),
    ]
