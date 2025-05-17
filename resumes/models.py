# File: resumes/models.py
# Author: Oluwatobiloba Light
"""Resume"""

from django.core.validators import MinLengthValidator, RegexValidator
from django.db import models

from users.models import User


class Resume(models.Model):
    """Resume Model"""

    # Personal Info
    first_name = models.CharField(blank=False, max_length=255)
    last_name = models.CharField(blank=False, max_length=255)

    # Contact Info
    email = models.EmailField(max_length=255, blank=False, db_index=True)
    phone_number = models.CharField(
        max_length=20,
        validators=[RegexValidator(r"^\+?1?\d{9,15}$")],
        blank=True,
    )

    # Work Experience
    work_experience = models.JSONField(
        default=list, validators=[MinLengthValidator(1)]
    )

    # Education
    education = models.JSONField(
        default=list, validators=[MinLengthValidator(1)]
    )

    # Language
    languages = models.JSONField(
        default=list, validators=[MinLengthValidator(1)]
    )

    # Skills & Certifications
    skills = models.JSONField(default=list)
    certifications = models.JSONField(default=list)

    # Resume Content
    resume_summary = models.TextField(
        db_index=True, help_text="Professional summary of the candidate"
    )

    # Original AI Response
    original_content = models.TextField(
        help_text="Original markdown content from AI generation", blank=True
    )

    # PDF Storage
    pdf_url = models.URLField(
        max_length=500, blank=True, help_text="URL to the generated PDF resume"
    )

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="resumes", db_index=True
    )

    # more fields to be added later (can't think of any right now)
    update_generate_content_count: int = models.PositiveIntegerField(default=1)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Resume for {self.user.email} (ID: {self.id})"
