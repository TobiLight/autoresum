# Generated by Django 5.1.3 on 2025-03-10 22:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("resumes", "0002_alter_resume_email_alter_resume_resume_summary"),
    ]

    operations = [
        migrations.AddField(
            model_name="resume",
            name="original_content",
            field=models.TextField(
                blank=True,
                help_text="Original markdown content from AI generation",
            ),
        ),
        migrations.AddField(
            model_name="resume",
            name="pdf_url",
            field=models.URLField(
                blank=True,
                help_text="URL to the generated PDF resume",
                max_length=500,
            ),
        ),
        migrations.AlterField(
            model_name="resume",
            name="resume_summary",
            field=models.TextField(
                db_index=True, help_text="Professional summary of the candidate"
            ),
        ),
    ]
