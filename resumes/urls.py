# File: resumes/urls.py
# Author: Oluwatobiloba Light
"""Resume Urls"""

from django.urls import path

from resumes.views import (
    GenerateAIContentView,
    GeneratedAIContentView,
    # ResumeCreateView,  # DEPRECATED: Functionality moved to GeneratedAIContentView
    ResumeResultView,
    ResumeUpdateView,
    # UpdateAIResumeView,  # DEPRECATED: Functionality moved to UpdatedGeneratedAIContentView
    UpdatedGeneratedAIContentView,
    UpdateGenerateAIContentView,
)

urlpatterns = [
    # Core 2-endpoint flow for resume generation
    path("generate", GenerateAIContentView.as_view(), name="generated_resume"),
    path(
        "generated/<str:resume_content_id>",
        GeneratedAIContentView.as_view(),
        name="generated_resume_content",
    ),

    # Resume update flow (2-endpoint pattern)
    path(
        "generate/update/<str:resume_id>",
        UpdateGenerateAIContentView.as_view(),
        name="update_generate_resume",
    ),
    path(
        "generated/update/<str:resume_content_id>",
        UpdatedGeneratedAIContentView.as_view(),
        name="update_generated_resume_content",
    ),

    # Resume management endpoints
    path("<str:resume_id>", ResumeResultView.as_view(), name="view_resume"),
    path(
        "update/<int:resume_id>",
        ResumeUpdateView.as_view(),
        name="resume_update",
    ),

    # DEPRECATED ENDPOINTS - Functionality moved to enhanced views above
    # path("create", ResumeCreateView.as_view(), name="create_resume"),  # Use "generated/<id>" instead
    # path(
    #     "update/generated/<str:resume_task_id>",
    #     UpdateAIResumeView.as_view(),
    #     name="update_resume_ai_generated",
    # ),  # Use "generated/update/<id>" instead
]
