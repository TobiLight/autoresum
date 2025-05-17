from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from users.models import User


class UserRegistrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse("register")
        self.valid_payload = {
            "username": "janetdoe",
            "email": "janetdoe@example.com",
            "password": "SecurePass123",
            "first_name": "Janet",
            "last_name": "Doe",
        }

    def test_valid_registration(self):
        user1 = {
            "username": "janetdoe1",
            "email": "janetdoe1@example.com",
            "password": "SecurePass123",
            "confirm_password": "SecurePass123",
            "first_name": "Janetta",
            "last_name": "Doemi",
        }
        response = self.client.post(self.register_url, user1, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            User.objects.filter(email="janetdoe1@example.com").exists()
        )

    def test_duplicate_email(self):
        User.objects.create_user(**self.valid_payload)
        response = self.client.post(
            self.register_url, self.valid_payload, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_email(self):
        payload = {**self.valid_payload, "email": "invalid-email"}
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_short_password(self):
        payload = {**self.valid_payload, "password": "weak"}
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_weak_password(self):
        payload = {**self.valid_payload, "password": "weakpassword"}
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_match(self):
        """Tests if password and confirm_password are equal"""
        payload = {
            **self.valid_payload,
            "password": "Securepassword1",
            "confirm_password": "Securepassword",
        }
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_names(self):
        for field in ["first_name", "last_name"]:
            payload = {**self.valid_payload}
            payload[field] = ""
            response = self.client.post(
                self.register_url, payload, format="json"
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
