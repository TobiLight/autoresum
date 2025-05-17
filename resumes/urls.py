# File: resumes/urls.py
# Author: Oluwatobiloba Light
"""Resume Urls"""

from django.urls import path

from resumes.views import (
    GenerateAIContentView,
    GeneratedAIContentView,
    ResumeCreateView,
    ResumeResultView,
    ResumeUpdateView,
    UpdateAIResumeView,
    UpdatedGeneratedAIContentView,
    UpdateGenerateAIContentView,
)

urlpatterns = [
    path("generate", GenerateAIContentView.as_view(), name="generated_resume"),
    path(
        "generated/<str:resume_content_id>",
        GeneratedAIContentView.as_view(),
        name="generated_resume_content",
    ),
    path(
        "generate/update/<str:resume_id>",
        UpdateGenerateAIContentView.as_view(),
        name="update_generate_resume",
    ),
    path(
        "generated/update/<str:resume_content_id>",
        UpdatedGeneratedAIContentView.as_view(),
        name="update_generate_resume",
    ),
    path("create", ResumeCreateView.as_view(), name="create_resume"),
    path("<str:resume_id>", ResumeResultView.as_view(), name="view_resume"),
    path(
        "update/generated/<str:resume_task_id>",
        UpdateAIResumeView.as_view(),
        name="update_resume_ai_generated",
    ),
    path(
        "update/<int:resume_id>",
        ResumeUpdateView.as_view(),
        name="resume_update",
    ),
]
