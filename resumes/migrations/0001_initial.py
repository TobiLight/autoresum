# Generated by Django 4.2.19 on 2025-03-04 22:14

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Resume",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("first_name", models.CharField(max_length=255)),
                ("last_name", models.CharField(max_length=255)),
                (
                    "email",
                    models.EmailField(
                        db_index=True, max_length=255, unique=True
                    ),
                ),
                (
                    "phone_number",
                    models.CharField(
                        blank=True,
                        max_length=20,
                        validators=[
                            django.core.validators.RegexValidator(
                                "^\\+?1?\\d{9,15}$"
                            )
                        ],
                    ),
                ),
                (
                    "work_experience",
                    models.JSONField(
                        default=list,
                        validators=[
                            django.core.validators.MinLengthValidator(1)
                        ],
                    ),
                ),
                (
                    "education",
                    models.JSONField(
                        default=list,
                        validators=[
                            django.core.validators.MinLengthValidator(1)
                        ],
                    ),
                ),
                (
                    "language",
                    models.JSONField(
                        default=list,
                        validators=[
                            django.core.validators.MinLengthValidator(1)
                        ],
                    ),
                ),
                ("skills", models.JSONField(default=list)),
                ("certifications", models.JSONField(default=list)),
                (
                    "resume_summary",
                    models.CharField(db_index=True, max_length=255),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("modified_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="resumes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
