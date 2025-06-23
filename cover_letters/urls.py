# File: cover_letters/urls.py
# Author: Oluwatobiloba Light
"""Cover Letters Urls"""

from django.urls import path

from .views import (
    # CoverLetterCreateView,  # DEPRECATED: Functionality moved to ViewGeneratedCoverLetterContentView
    CoverLetterResultView,
    CoverLetterUpdateView,
    GenerateAICoverLetterContentView,
    UpdateGenerateAICoverLetterContentView,
    UpdatedGeneratedAICoverLetterContentView,
    # UpdateAICoverLetterView,  # DEPRECATED: Functionality moved to UpdatedGeneratedAICoverLetterContentView
    ViewGeneratedCoverLetterContentView,
)

urlpatterns = [
    # Core 2-endpoint flow for cover letter generation
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

    # Cover letter update flow (2-endpoint pattern)
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

    # Cover letter management endpoints
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

    # DEPRECATED ENDPOINTS - Functionality moved to enhanced views above
    # path(
    #     "create",
    #     CoverLetterCreateView.as_view(),
    #     name="create_cover_letter",
    # ),  # Use "generated/<id>" instead
    # path("update/generated/<str:cover_letter_task_id>", UpdateAICoverLetterView.as_view(), name="update_cover_letter_ai"),  # Use "generated/update/<id>" instead
]
