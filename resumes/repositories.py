# File: resumes/repositories.py
# Author: Oluwatobiloba Light
"""Resume Repository"""
import json
from datetime import datetime

from django.core.cache import cache

from resumes.models import Resume
from users.models import User


class ResumeRepository:
    """Handles business logic for AI resume generation."""

    def __init__(self, resume_generator):
        self.resume_generator = resume_generator

    def generate_resume_content(self, user_data: dict, user_id: int) -> str:
        """Trigger async celery task"""
        from resumes.tasks import generate_resume_content_task

        task = generate_resume_content_task.apply_async(
            args=[user_data, user_id]
        )

        return task.id

    def update_resume_content(
        self, resume_id: str, user_data: dict, user_id: int
    ) -> str:
        """Trigger async celery task"""
        from resumes.tasks import update_resume_content_task

        task = update_resume_content_task.apply_async(
            args=[resume_id, user_data, user_id]
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

    def forget_task(self):
        self.resume_generator.forget()

    def create_resume(
        self, original_resume_content: str, content: dict, user: User
    ):
        """Create a resume"""

        try:
            resume = Resume.objects.create(
                first_name=content.get("full_name").split(" ")[0],
                last_name=content.get("full_name").split(" ")[1],
                email=user.email,
                work_experience=content.get("work_experience", []),
                education=content.get("education", []),
                skills=content.get("skills", []),
                resume_summary=content.get("resume_summary", ""),
                certifications=content.get("certifications", []),
                languages=content.get("languages", []),
                phone_number=content.get("phone_number", "+12345678901"),
                original_content=original_resume_content,
                user=user,
            )

            return resume
        except Exception:
            raise

    def update_resume(
        self, resume_id, original_resume_content: str, content: dict, user: User
    ):
        """Create a resume"""
        try:

            update_fields = {
                key: value
                for key, value in content.items()
                if key
                in [
                    "email",
                    "work_experience",
                    "education",
                    "skills",
                    "languages",
                    "certifications",
                    "phone_number",
                    "resume_summary",
                ]
            }

            temp = {
                "first_name": content.get("full_name", "John Doe").split(" ")[
                    0
                ],
                "last_name": content.get("full_name", "John Doe").split(" ")[1],
                **update_fields,
            }
            update = Resume.objects.filter(id=resume_id).update(
                **temp,
                original_content=original_resume_content,
                modified_at=datetime.now(),
            )
            return True if update > 0 else False
        except Exception:
            raise
