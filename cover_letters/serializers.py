# File: cover_letters/serializers.py
# Author: Oluwatobiloba Light
"""Cover Letter Serializer"""

from django.core.validators import RegexValidator
from rest_framework import serializers

from .models import CoverLetter


class CreateCoverLetterSerializer(serializers.Serializer):
    cover_letter_task_id = serializers.CharField(required=True)

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


class UpdateCoverLetterSerializer(serializers.Serializer):
    cover_letter_id = serializers.CharField(required=True)

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


class GenerateCoverLetterSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=True, max_length=255)

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
    company_name = serializers.CharField(required=True, max_length=255)
    job_title = serializers.CharField(required=True, max_length=255)
    job_description = serializers.CharField(required=True)
    hiring_manager = serializers.CharField(required=False, max_length=255)
    reason_for_applying = serializers.CharField(required=False)


class CoverLetterSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(required=False, allow_blank=True, source="name")
    email = serializers.EmailField(required=False, allow_blank=True)
    job_description = serializers.CharField(required=False, allow_blank=True)
    hiring_manager = serializers.CharField(required=False, allow_blank=True)
    reason_for_applying = serializers.CharField(
        required=False, allow_blank=True
    )
    phone_number = serializers.CharField(
        required=False,
        max_length=20,
        validators=[RegexValidator(r"^\+?1?\d{9,15}$")],
        allow_blank=True,
    )

    class Meta:
        model = CoverLetter
        fields = [
            "full_name",
            "email",
            "phone_number",
            "company_name",
            "job_title",
            "job_description",
            "hiring_manager",
            "reason_for_applying",
            "generated_content",
            "parsed_content",
        ]
        read_only_fields = (
            "user",
            "generated_content",
            "parsed_content",
            "pdf_url",
            "created_at",
            "modified_at",
        )

    def create(self, validated_data):
        # Assign the authenticated user before saving
        user = self.context["request"].user
        validated_data["user"] = user
        return super().create(validated_data)
