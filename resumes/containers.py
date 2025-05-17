# File: containers.py
# Author: Oluwatobiloba Light

from dependency_injector import containers, providers
from django.conf import settings

from resumes.repositories import ResumeRepository
from resumes.services.ai_generator import OpenAIResumeGenerator


class Container(containers.DeclarativeContainer):
    """Dependency injection container."""

    config = settings

    # AI Service
    ai_service = providers.Singleton(
        OpenAIResumeGenerator,
        api_key=config.OPENAI_API_KEY,
        organization_id=config.OPENAI_ORGANIZATION_ID,
    )

    resume_service = providers.Singleton(ai_service)
    resume_repository = providers.Factory(
        ResumeRepository, resume_generator=resume_service
    )
