# File: cover_letters/repositories.py
# Author: Oluwatobiloba Light
"""Cover letter repository"""

from datetime import datetime
import json

from django.core.cache import cache

from cover_letters.models import CoverLetter
from users.models import User


class CoverLetterRepository:
    """Handles business logic for AI CoverLetter generation."""

    def __init__(self, cover_letter_generator):
        self.cover_letter_generator = cover_letter_generator

    def generate_cover_letter_content(
        self, user_data: dict, user_id: int
    ) -> str:
        """Trigger async Celery task and return task ID."""
        from cover_letters.tasks import generate_cover_letter_content_task

        task = generate_cover_letter_content_task.apply_async(args=[user_data, user_id])

        return task.id

    def update_cover_letter_content(
        self, cover_letter_id: str, user_data: dict, user_id: int
    ) -> str:
        """Trigger async Celery task and return task ID."""
        from cover_letters.tasks import update_cover_letter_content_task

        task = update_cover_letter_content_task.apply_async(
            args=[cover_letter_id, user_data, user_id]
        )

        return task.id

    def save_task_result(self, key: str, result: dict):
        """Save completed task result as JSON in Redis."""
        cache.set(key, json.dumps(result), timeout=600)

    def get_task_status(self, task_id: str):
        """Retrieve task status"""
        result = cache.get(task_id)
        return json.loads(result) if result else None

    def get_task_result(self, key: str):
        """Retrieve task result from Redis and convert JSON string back to dict."""
        result = cache.get(key)
        return json.loads(result) if result else None

    def delete_task(self, key: str):
        """Delete task result from redis"""
        cache.delete(key)

    def create_cover_letter(
        self, original_cover_letter_content: str, content: dict, user: User
    ):
        """Create a cover letter"""
        try:
            cover_letter = CoverLetter.objects.create(
                name=content.get("name"),
                email=content.get("email"),
                phone_number=content.get("phone", None),
                cover_letter_content=content.get("cover_letter"),
                company_name=content.get("company_name"),
                job_title=content.get("job_title"),
                parsed_content=content,
                generated_content=original_cover_letter_content,
                user=user,
            )

            return cover_letter
        except Exception:
            raise

    def update_cover_letter(
        self,
        cover_letter_id,
        original_cover_letter_content: str,
        content: dict,
        user: User,
    ):
        """Create a cover_letter"""
        try:
            print("content,", content.items())

            update_fields = {
                key: value
                for key, value in content.items()
                if key
                in [
                    "email",
                    "phone_number",
                    "cover_letter_content",
                    "company_name",
                    "job_title",
                ]
            }

            temp = {
                "name": content.get("full_name", "John Doe"),
                **update_fields,
            }
            update = CoverLetter.objects.filter(id=cover_letter_id, user=user).update(
                **temp,
                generated_content=original_cover_letter_content,
                modified_at=datetime.now(),
            )
            return True if update > 0 else False
        except:
            raise
