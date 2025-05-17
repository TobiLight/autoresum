# File: cover_letters/urls.py
# Author: Oluwatobiloba Light
"""Cover Letters Urls"""

from django.urls import path

from .views import (
    CoverLetterCreateView,
    CoverLetterResultView,
    CoverLetterUpdateView,
    GenerateAICoverLetterContentView,
    UpdateGenerateAICoverLetterContentView,
    UpdatedGeneratedAICoverLetterContentView,
    UpdateAICoverLetterView,
    ViewGeneratedCoverLetterContentView,
)

urlpatterns = [
    path(
        "create",
        CoverLetterCreateView.as_view(),
        name="create_cover_letter",
    ),
    path(
        "generate",
        GenerateAICoverLetterContentView.as_view(),
        name="generate_cover_letter_content",
    ),
    path(
        "generated/<str:cover_letter_task_id>",
        ViewGeneratedCoverLetterContentView.as_view(),
        name="view_generated_cover_letter_content",
    ),
    path(
        "generate/update/<str:cover_letter_id>",
        UpdateGenerateAICoverLetterContentView.as_view(),
        name="update_generate_cover_letter_content",
    ),
    path(
        "generated/update/<str:cover_letter_content_id>",
        UpdatedGeneratedAICoverLetterContentView.as_view(),
        name="update_generated_cover_letter_content",
    ),
    path("update/generated/<str:cover_letter_task_id>", UpdateAICoverLetterView.as_view(), name="update_cover_letter_ai"),
    path(
        "update/<int:cover_letter_id>",
        CoverLetterUpdateView.as_view(),
        name="update_cover_letter",
    ),
    path(
        "<str:cover_letter_id>",
        CoverLetterResultView.as_view(),
        name="view_cover_letter",
    ),
]
