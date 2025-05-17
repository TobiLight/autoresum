# File: cover_letters/models.py
# Author: Oluwatobiloba Light
"""Cover Letter Database Model"""

from django.core.validators import RegexValidator
from django.db import models

from users.models import User


class CoverLetter(models.Model):
    """Cover Letter Model"""

    name: str = models.CharField(blank=False, max_length=255)

    email = models.EmailField(max_length=255, blank=False, db_index=True)
    phone_number = models.CharField(
        max_length=20,
        validators=[RegexValidator(r"^\+?1?\d{9,15}$")],
        blank=True,
    )

    cover_letter_content: str = models.TextField(blank=False, db_index=True)

    company_name: str = models.CharField(
        blank=False, max_length=255, help_text="Company name"
    )

    job_title: str = models.CharField(
        blank=False, max_length=255, help_text="User job title"
    )

    # CoverLetter Content
    parsed_content = models.TextField(
        db_index=True, help_text="Professional cover letter of the candidate"
    )

    # Original AI Response
    generated_content = models.TextField(
        help_text="Original markdown content from AI generation", blank=True
    )

    # PDF Storage
    pdf_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="URL to the generated PDF Cover Letter",
    )

    update_generate_content_count: int = models.PositiveIntegerField(default=1)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="cover_letters",
        db_index=True,
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cover Letter created for {self.user.email} (ID: {self.id})"
