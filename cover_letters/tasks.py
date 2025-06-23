# File: cover_letters/tasks.py
# Author: Oluwatobiloba Light
"""Cover Letter celery shared task"""

from typing import Union
from celery import shared_task

from cover_letters.containers import Container
from cover_letters.models import CoverLetter
from users.models import User


@shared_task
def generate_cover_letter_content_task(user_data: dict, user_id: int):
    """Celery task to generate a cover letter asynchronously."""

    cover_letter_service = Container.cover_letter_service()

    cover_letter_content = cover_letter_service.generate_cover_letter_content(
        user_data
    )
    parsed_data = cover_letter_service.parse_cover_letter_content(
        cover_letter_content
    )

    return {"original_content": cover_letter_content, "parsed_content": parsed_data}


@shared_task
def update_cover_letter_content_task(cover_letter_id: str, user_data: dict, user_id: int):
    """Celery task to generate a cover letter asynchronously."""
    user: Union[User, None] = None
    cover_letter: Union[CoverLetter, None] = None

    try:
        # Fetch the user inside Celery
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise ValueError(f"User with id {user_id} not found.")

    try:
        cover_letter = CoverLetter.objects.get(id=cover_letter_id, user=user)
    except:
        raise ValueError(f"Cover letter with id {user_id} or user_id {user_id} not found.")

    cover_letter_service = Container.cover_letter_service()

    cover_letter_content = cover_letter_service.generate_cover_letter_content(user_data)
    parsed_data = cover_letter_service.parse_cover_letter_content(cover_letter_content)

    cover_letter.update_generate_content_count += 1
    cover_letter.save(update_fields=["update_generate_content_count"])

    return {
        "original_content": cover_letter_content,
        "parsed_content": parsed_data,
        "cover_letter_id": cover_letter_id  # Include cover_letter_id for automatic update functionality
    }
