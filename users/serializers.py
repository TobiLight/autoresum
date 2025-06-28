# File: users/serializers.py
# Author: Oluwatobiloba Light

from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class UserSerializer(serializers.HyperlinkedModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
    )

    confirm_password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "confirm_password",
            "first_name",
            "last_name",
            "created_at",
            "modified_at",
        ]

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )

        return data

    def validate_password(self, value):
        validate_password(value)
        return value

    def get_help_text(self):
        return "Your password must be at least 8 characters long and contain digits, uppercase and lowercase letters, and special characters."

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        user = User.objects.create_user(**validated_data)
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for viewing user profile information."""

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "date_joined",
            "last_login",
            "created_at",
            "modified_at",
            "is_active",
        ]
        read_only_fields = [
            "id",
            "username",
            "date_joined",
            "last_login",
            "created_at",
            "modified_at",
            "is_active",
        ]


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile information."""

    email = serializers.EmailField(required=False)
    first_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=255, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
        ]

    def validate_email(self, value):
        """Validate that email is unique (excluding current user)."""
        user = self.instance
        if User.objects.filter(email=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_first_name(self, value):
        """Validate first name is not whitespace-only if provided."""
        if value is not None and value != "" and value.strip() == "":
            raise serializers.ValidationError("First name cannot be whitespace only.")
        return value

    def validate_last_name(self, value):
        """Validate last name is not whitespace-only if provided."""
        if value is not None and value != "" and value.strip() == "":
            raise serializers.ValidationError("Last name cannot be whitespace only.")
        return value
