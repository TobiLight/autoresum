from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from users.models import User


class UserLoginTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.login_url = reverse("login")
        self.user = User.objects.create_user(
            username="janetdoe",
            email="janetdoe@example.com",
            password="SecurePass123",
            first_name="Janet",
            last_name="Doe",
        )

        self.valid_credentials = {
            "username": "janetdoe",
            "password": "SecurePass123",
        }

    def test_valid_login(self):
        response = self.client.post(
            self.login_url, self.valid_credentials, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_invalid_username(self):
        invalid_credentials = {
            "username": "johndoe",
            "password": "SecurePass123",
        }
        response = self.client.post(
            self.login_url, invalid_credentials, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_password(self):
        invalid_credentials = {
            "username": "janetdoe@example.com",
            "password": "WrongPass123",
        }
        response = self.client.post(
            self.login_url, invalid_credentials, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_email(self):
        invalid_credentials = {"password": "SecurePass123"}
        response = self.client.post(
            self.login_url, invalid_credentials, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_password(self):
        invalid_credentials = {"username": "janetdoe"}
        response = self.client.post(
            self.login_url, invalid_credentials, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
