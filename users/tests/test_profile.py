# File: users/tests/test_profile.py
# Author: Oluwatobiloba Light
"""User profile management tests"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


class UserProfileViewTest(TestCase):
    """Test the UserProfileView for retrieving user profile information."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="testpass123",
            first_name="John",
            last_name="Doe",
        )

    def test_get_profile_authenticated_user(self):
        """Test that authenticated users can retrieve their profile."""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get("/api/auth/profile")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "Success")
        self.assertEqual(response.data["message"], "Profile retrieved successfully")
        self.assertIn("user", response.data)
        
        user_data = response.data["user"]
        self.assertEqual(user_data["username"], "testuser")
        self.assertEqual(user_data["email"], "testuser@example.com")
        self.assertEqual(user_data["first_name"], "John")
        self.assertEqual(user_data["last_name"], "Doe")
        self.assertIn("id", user_data)
        self.assertIn("date_joined", user_data)
        self.assertIn("is_active", user_data)

    def test_get_profile_unauthenticated_user(self):
        """Test that unauthenticated users cannot retrieve profile."""
        response = self.client.get("/api/auth/profile")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_contains_readonly_fields(self):
        """Test that profile response contains all expected readonly fields."""
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/auth/profile")
        user_data = response.data["user"]
        
        readonly_fields = ["id", "username", "date_joined", "created_at", "modified_at", "is_active"]
        for field in readonly_fields:
            self.assertIn(field, user_data)


class UserProfileUpdateViewTest(TestCase):
    """Test the UserProfileUpdateView for updating user profile information."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="testpass123",
            first_name="John",
            last_name="Doe",
        )
        self.client.force_authenticate(user=self.user)

    def test_update_profile_patch_success(self):
        """Test successful profile update using PATCH."""
        update_data = {
            "first_name": "Jane",
            "last_name": "Smith",
        }
        
        response = self.client.patch("/api/auth/profile", update_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "Success")
        self.assertEqual(response.data["message"], "Profile updated successfully")

        user_data = response.data["user"]
        self.assertEqual(user_data["first_name"], "Jane")
        self.assertEqual(user_data["last_name"], "Smith")
        self.assertEqual(user_data["email"], "testuser@example.com")  # Unchanged

        # Verify database was updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Jane")
        self.assertEqual(self.user.last_name, "Smith")

    def test_update_profile_put_success(self):
        """Test successful profile update using PUT."""
        update_data = {
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane.smith@example.com",
        }

        response = self.client.put("/api/auth/profile", update_data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "Success")
        
        user_data = response.data["user"]
        self.assertEqual(user_data["first_name"], "Jane")
        self.assertEqual(user_data["last_name"], "Smith")
        self.assertEqual(user_data["email"], "jane.smith@example.com")

    def test_update_email_success(self):
        """Test successful email update."""
        update_data = {"email": "newemail@example.com"}
        
        response = self.client.patch("/api/auth/profile", update_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user_data = response.data["user"]
        self.assertEqual(user_data["email"], "newemail@example.com")

        # Verify database was updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "newemail@example.com")

    def test_update_email_duplicate_fails(self):
        """Test that updating to an existing email fails."""
        # Create another user with a different email
        User.objects.create_user(
            username="otheruser",
            email="existing@example.com",
            password="testpass123",
        )

        update_data = {"email": "existing@example.com"}

        response = self.client.patch("/api/auth/profile", update_data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["status"], "Failed")
        self.assertIn("errors", response.data)
        self.assertIn("email", response.data["errors"])

    def test_update_invalid_email_fails(self):
        """Test that updating with invalid email format fails."""
        update_data = {"email": "invalid-email"}
        
        response = self.client.patch("/api/auth/profile", update_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["status"], "Failed")
        self.assertIn("errors", response.data)

    def test_update_with_valid_names(self):
        """Test that updating with valid names works correctly."""
        update_data = {"first_name": "ValidName", "last_name": "ValidLastName"}

        response = self.client.patch("/api/auth/profile", update_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "Success")

        # Verify database was updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "ValidName")
        self.assertEqual(self.user.last_name, "ValidLastName")

    def test_update_empty_strings_allowed(self):
        """Test that empty strings are allowed for optional fields."""
        update_data = {"first_name": "", "last_name": ""}

        response = self.client.patch("/api/auth/profile", update_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "Success")

        # Verify database was updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "")
        self.assertEqual(self.user.last_name, "")

    def test_update_profile_unauthenticated_fails(self):
        """Test that unauthenticated users cannot update profile."""
        self.client.force_authenticate(user=None)

        update_data = {"first_name": "Jane"}
        response = self.client.patch("/api/auth/profile", update_data)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_partial_update_only_provided_fields(self):
        """Test that partial update only changes provided fields."""
        original_email = self.user.email
        original_last_name = self.user.last_name

        update_data = {"first_name": "UpdatedName"}

        response = self.client.patch("/api/auth/profile", update_data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        user_data = response.data["user"]
        self.assertEqual(user_data["first_name"], "UpdatedName")
        self.assertEqual(user_data["email"], original_email)  # Unchanged
        self.assertEqual(user_data["last_name"], original_last_name)  # Unchanged


class UserProfileSecurityTest(TestCase):
    """Test security aspects of user profile endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            username="user1",
            email="user1@example.com",
            password="testpass123",
        )
        self.user2 = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="testpass123",
        )

    def test_user_can_only_access_own_profile(self):
        """Test that users can only access their own profile data."""
        self.client.force_authenticate(user=self.user1)
        
        response = self.client.get("/api/auth/profile")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user_data = response.data["user"]
        self.assertEqual(user_data["username"], "user1")
        self.assertEqual(user_data["email"], "user1@example.com")

    def test_user_can_only_update_own_profile(self):
        """Test that users can only update their own profile data."""
        self.client.force_authenticate(user=self.user1)

        update_data = {"first_name": "Updated"}
        response = self.client.patch("/api/auth/profile", update_data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify user1 was updated
        self.user1.refresh_from_db()
        self.assertEqual(self.user1.first_name, "Updated")
        
        # Verify user2 was not affected
        self.user2.refresh_from_db()
        self.assertNotEqual(self.user2.first_name, "Updated")
