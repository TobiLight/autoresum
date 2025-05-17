# File: cover_letters/containers.py
# Author: Oluwatobiloba Light
"""Cover letter dependency container"""
from dependency_injector import containers, providers
from django.conf import settings

from cover_letters.repositories import CoverLetterRepository
from cover_letters.services.ai_generator import OpenAICoverLetterGenerator


class Container(containers.DeclarativeContainer):
    """Dependency injection container."""

    config = settings

    # AI Service
    ai_service = providers.Singleton(
        OpenAICoverLetterGenerator,
        api_key=config.OPENAI_API_KEY,
        organization_id=config.OPENAI_ORGANIZATION_ID,
    )

    cover_letter_service = providers.Singleton(ai_service)

    cover_letter_repository = providers.Factory(
        CoverLetterRepository, cover_letter_generator=cover_letter_service
    )
