# File: resumes/serializers.py
# Author: Oluwatobiloba Light
"""Resume Serializer"""

from django.core.validators import MinLengthValidator, RegexValidator
from rest_framework import serializers

from .models import Resume


class CreateResumeSerializer(serializers.Serializer):
    resume_task_id = serializers.CharField(required=True)

    def create(self, validated_data):
        # Assign the authenticated user before saving
        if "request" in self.context:
            user = self.context["request"].user
        else:
            user = validated_data.pop("user", None)

        if not user:
            raise serializers.ValidationError("User is required.")

        validated_data["user"] = user
        return super().create(validated_data)

class UpdateResumeSerializer(serializers.Serializer):
    resume_id = serializers.CharField(required=True)

    def create(self, validated_data):
        # Assign the authenticated user before saving
        if "request" in self.context:
            user = self.context["request"].user
        else:
            user = validated_data.pop("user", None)

        if not user:
            raise serializers.ValidationError("User is required.")

        validated_data["user"] = user
        return super().create(validated_data)


class ResumeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Resume
        fields = "__all__"
        read_only_fields = (
            "user",
            "created_at",
            "updated_at",
            "resume_summary",
            "original_content",
            "pdf_url",
            "update_generate_content_count"
        )


class AIResumeSerializer(serializers.Serializer):
    # Personal Info
    first_name = serializers.CharField(required=True, max_length=255)
    last_name = serializers.CharField(required=True, max_length=255)

    # Contact Info
    email = serializers.EmailField(required=True, max_length=255)
    phone_number = serializers.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                r"^\+?[0-9\s\-\(\)]{7,20}$",
                message="Enter a valid phone number",
            )
        ],
        required=False,
    )

    # Work Experience
    work_experience = serializers.JSONField(
        default=list, validators=[MinLengthValidator(1)]
    )

    # Education
    education = serializers.JSONField(
        default=list, validators=[MinLengthValidator(1)]
    )

    # Language
    languages = serializers.JSONField(
        default=list, validators=[MinLengthValidator(1)]
    )

    # Skills & Certifications
    skills = serializers.JSONField(default=list)
    certifications = serializers.JSONField(default=list)
