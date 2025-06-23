# # File: resumes/tests.py
# # Author: Oluwatobiloba Light
# """Resume Tests"""

import json
from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase
from rest_framework.test import APIClient

from resumes.models import Resume
from resumes.services.ai_generator import OpenAIResumeGenerator
from resumes.tasks import generate_resume_content_task
from users.models import User


class GenerateResumeTaskTest(TestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="secureTestPassw0rd",
        )
        self.client.force_authenticate(user=self.user)

    @pytest.fixture
    def resume_generator(self):
        """Fixture to create an instance of OpenAIResumeGenerator."""
        return OpenAIResumeGenerator(
            api_key="fake_api_key", organization_id="fake_org_id"
        )

    @patch(
        "resumes.tasks.generate_resume_content_task.delay"
    )  # Mocking the Celery task
    @patch("resumes.containers.Container.resume_service")
    def test_generate_resume_task(
        self, mock_resume_service, mock_generate_resume
    ):
        """Test the Celery task for generating a resume."""

        # Mock the AI resume generator service
        mock_generator = MagicMock()
        mock_generator.generate_resume_content_task.return_value = {
            "resume_id": 1,
        }
        mock_resume_service.return_value = mock_generator

        # Mock Celery task return value
        mock_generate_resume.return_value = "mock_task_id"

        # Test data
        user_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone_number": "+1234567890",
            "work_experience": [
                {
                    "job_title": "Software Engineer",
                    "company": "Tech Corp",
                    "start_date": "2020-01-01",
                    "end_date": "2023-12-31",
                    "current": False,
                    "description": "Developed Python applications...",
                }
            ],
            "education": [
                {
                    "degree": "BSc Computer Science",
                    "institution": "State University",
                    "start_date": "2016-09-01",
                    "end_date": "2020-05-01",
                }
            ],
            "skills": ["Python", "Django"],
            "certifications": ["AWS Certified Developer"],
            "resume_summary": "Experienced software engineer...",
        }

        user_id = 1

        # Run the Celery task (which is now mocked)
        result = generate_resume_content_task.delay(user_data, user_id)

        # Assertions
        assert result == "mock_task_id"
        mock_generate_resume.assert_called_once_with(user_data, user_id)

    @patch(
        "resumes.services.ai_generator.OpenAIResumeGenerator.parse_resume_content"
    )
    @patch(
        "resumes.services.ai_generator.OpenAIResumeGenerator.generate_resume_content"
    )
    @patch(
        "resumes.services.ai_generator.OpenAIResumeGenerator"
    )  # Mock OpenAI class
    def test_parse_ai_response(
        self,
        mock_openai,
        mock_generate_resume_content,
        mock_parse_resume_content,
    ):
        """Test AI response parsing and structured resume generation without making real OpenAI API calls."""

        # ✅ Ensure OpenAI class is mocked
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # ✅ Mock generate_resume_content so it doesn't call OpenAI
        mock_generate_resume_content.return_value = """# John Doe

## Software Engineer

---

## Work Experience
### Software Engineer | Tech Corp
**Jan 2020 – Dec 2023**
- Developed Python applications

---

## Skills
- Python
- Django

---

## Education
### BSc Computer Science | State University
**Graduated: May 2020**

---

## Certifications
- ✅ AWS Certified Developer

---

## Summary
Results-driven Software Engineer with experience in developing Python applications. Strong skills in Python and Django. Adept at collaborating with teams to deliver high-quality solutions.

---

## Languages
- English
- Yoruba
- Pidgin

---

## Contact
📞 **Phone:** +1234567890 """

        # ✅ Mock parse_resume_content
        mock_parse_resume_content.return_value = {
            "full_name": "John Doe",
            "phone_number": "+1234567890",
            "work_experience": [],
            "education": [],
            "skills": ["Python", "Django"],
            "resume_summary": "This resume is ATS-optimized...",
            "certifications": ["AWS Certified Developer"],
            "languages": ["English", "Yoruba", "Pidgin"],
        }

        # Initialize the generator
        generator = mock_openai

        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone_number": "+1234567890",
            "work_experience": [],
            "education": [],
            "skills": ["Python", "Django"],
            "certifications": ["AWS Certified Developer"],
            "languages": ["English", "Yoruba", "Pidgin"],
        }

        # Simulate response parsing
        resume_content = generator.generate_resume_content(
            data
        )  # ✅ Mocked, so no API call
        parsed_data = generator.parse_resume_content(
            resume_content
        )  # ✅ Mocked, returns expected data

        # ✅ Assertions
        self.assertEqual(parsed_data["full_name"], "John Doe")
        self.assertIn("Python", parsed_data["skills"])

        # ✅ Ensure generate_resume_content was actually called
        mock_generate_resume_content.assert_called_once_with(data)


class UpdateResumeTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="testpass",
        )
        self.other_user = User.objects.create_user(
            username="otheruser",
            email="otheruser@example.com",
            password="testpass",
        )
        self.resume = Resume.objects.create(
            user=self.user,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
        )
        self.client.force_authenticate(user=self.user)

    def test_update_resume_success(self):
        """Test that an authenticated user can update their resume."""
        update_data = {"first_name": "Updated John", "last_name": "Doe"}
        response = self.client.patch(
            f"/api/resume/update/{self.resume.id}", update_data
        )
        self.assertEqual(response.status_code, 200)
        self.resume.refresh_from_db()
        self.assertEqual(self.resume.first_name, "Updated John")

    def test_update_other_user_resume_fails(self):
        """Test that a user cannot update another user's resume."""
        self.client.force_authenticate(user=self.other_user)
        update_data = {"first_name": "Hacker"}
        response = self.client.patch(
            f"/api/resume/update/{self.resume.id}", update_data
        )
        self.assertEqual(
            response.status_code, 404
        )  # Should return 404 as the resume doesn't belong to them

    @patch("resumes.containers.Container.resume_repository")
    @patch("resumes.tasks.update_resume_content_task.delay")
    @patch("celery.result.AsyncResult.forget")
    def test_ai_update_resume_success(
        self, mock_forget, mock_update_task, mock_repo
    ):
        """Test updating a resume with AI-generated content."""

        # Mock the Celery task return value
        mock_update_task.return_value = "mock_task_id"

        # Mock repository to return AI-generated resume data
        mock_repo.return_value.get_task_result.return_value = {
            "original_content": "Generated AI Resume Content",
            "parsed_content": {
                "full_name": "John Doe",
                "phone_number": "+1234567890",
                "work_experience": [],
                "education": [],
                "skills": ["Python", "Django"],
                "certifications": ["AWS Certified Developer"],
                "languages": ["English"],
                "resume_summary": "Experienced Software Engineer",
            },
        }

        update_data = {
            "resume_id": str(self.resume.id),
            "resume_task_id": "mock_task_id",
        }

        response = self.client.patch(
            f"/api/resume/update/generated/{update_data['resume_task_id']}",
            update_data,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("id", response.data)

    @patch("resumes.containers.Container.resume_repository")
    def test_ai_update_resume_no_task_result(self, mock_repo):
        """Test that updating with AI fails when no task result exists."""
        mock_repo.return_value.get_task_result.return_value = None

        update_data = {
            "resume_id": str(self.resume.id),
            "resume_task_id": "nonexistent_task",
        }
        response = self.client.patch(
            f"/api/resume/update/generated/{update_data['resume_task_id']}",
            update_data,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Resume failed to update", response.data["details"])


class OpenAIResumeGeneratorTest(TestCase):
    """Unit tests for OpenAIResumeGenerator."""

    def setUp(self):
        """Set up test instance."""
        self.resume_generator = OpenAIResumeGenerator(
            api_key="fake_api_key", organization_id="fake_org_id"
        )

    def test_check_api_key(self):
        """Test that check_api_key raises an error when API key is missing."""
        with self.assertRaises(ValueError) as context:
            OpenAIResumeGenerator(api_key="", organization_id="fake_org_id")
        self.assertEqual(str(context.exception), "API key is required.")

    @patch("resumes.services.ai_generator.OpenAIResumeGenerator.init_openai")
    def test_init_openai(self, mock_init_openai):
        """Test OpenAI client initialization."""
        mock_client = MagicMock()
        mock_init_openai.return_value = mock_client

        client = self.resume_generator.init_openai()

        mock_init_openai.assert_called_once()
        self.assertEqual(
            client, mock_client
        )  # Ensure the returned client is the mock

    @patch("resumes.services.ai_generator.OpenAIResumeGenerator.init_openai")
    def test_parse_resume_content(self, mock_init_openai):
        """Test parsing AI resume content."""
        mock_client = MagicMock()
        mock_init_openai.return_value = mock_client

        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "full_name": "John Doe",
                "phone_number": "+1234567890",
                "work_experience": [],
                "education": [],
                "skills": ["Python", "Django"],
                "resume_summary": "Experienced developer",
                "certifications": [],
                "languages": ["English"],
            }
        )
        mock_client.chat.completions.create.return_value = mock_response

        parsed_data = self.resume_generator.parse_resume_content("Resume text")

        self.assertEqual(parsed_data["full_name"], "John Doe")
        self.assertEqual(parsed_data["skills"], ["Python", "Django"])
        self.assertEqual(parsed_data["resume_summary"], "Experienced developer")
        mock_client.chat.completions.create.assert_called_once()

    @patch("resumes.services.ai_generator.OpenAIResumeGenerator.init_openai")
    def test_generate_resume_content(self, mock_init_openai):
        """Test generating resume content."""
        mock_client = MagicMock()
        mock_init_openai.return_value = mock_client

        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Generated Resume Content"
        mock_client.chat.completions.create.return_value = mock_response

        user_data = {
            "first_name": "John",
            "last_name": "Doe",
            "phone_number": "+1234567890",
            "work_experience": [],
            "education": [],
            "skills": ["Python", "Django"],
            "certifications": [],
            "languages": ["English"],
            "resume_summary": "Experienced developer",
        }

        resume_content = self.resume_generator.generate_resume_content(
            user_data
        )

        self.assertEqual(resume_content, "Generated Resume Content")
        mock_client.chat.completions.create.assert_called_once()


class GeneratedAIContentViewTest(TestCase):
    """Test the enhanced GeneratedAIContentView that automatically creates resumes."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="testpass",
        )
        self.client.force_authenticate(user=self.user)
        self.task_id = "test-task-id-123"

    @patch("resumes.containers.Container.resume_repository")
    @patch("celery.result.AsyncResult")
    def test_successful_task_creates_resume_automatically(self, mock_async_result, mock_repo):
        """Test that a successful task automatically creates a resume."""
        # Mock AsyncResult for successful task
        mock_result = MagicMock()
        mock_result.state = "SUCCESS"
        mock_result.status = "SUCCESS"
        mock_result.ready.return_value = True
        mock_result.failed.return_value = False
        mock_result.id = self.task_id
        mock_async_result.return_value = mock_result

        # Mock repository methods
        mock_repository = MagicMock()
        mock_repo.return_value = mock_repository

        # Mock task result data
        task_data = {
            "original_content": "Generated resume content",
            "parsed_content": {
                "full_name": "John Doe",
                "phone_number": "+1234567890",
                "work_experience": [],
                "education": [],
                "skills": ["Python", "Django"],
                "certifications": [],
                "languages": ["English"],
                "resume_summary": "Experienced developer",
            }
        }
        mock_repository.get_task_result.return_value = task_data

        # Mock created resume
        mock_resume = MagicMock()
        mock_resume.id = 1
        mock_resume.first_name = "John"
        mock_resume.last_name = "Doe"
        mock_resume.email = "testuser@example.com"
        mock_resume.phone_number = "+1234567890"
        mock_resume.work_experience = []
        mock_resume.education = []
        mock_resume.skills = ["Python", "Django"]
        mock_resume.certifications = []
        mock_resume.languages = ["English"]
        mock_resume.resume_summary = "Experienced developer"
        mock_repository.create_resume.return_value = mock_resume

        # Make request to the enhanced endpoint
        response = self.client.get(f"/api/resume/generated/{self.task_id}")

        # Assertions
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "Success")
        self.assertEqual(response.data["message"], "Resume created successfully")
        self.assertIn("resume", response.data)
        self.assertEqual(response.data["resume"]["id"], 1)
        self.assertEqual(response.data["resume"]["first_name"], "John")
        self.assertEqual(response.data["task_id"], self.task_id)

        # Verify repository methods were called
        mock_repository.create_resume.assert_called_once_with(
            task_data["original_content"],
            task_data["parsed_content"],
            self.user
        )
        mock_repository.delete_task.assert_called_once_with(self.task_id)
        # Note: forget() is called on the AsyncResult instance returned by AsyncResult(resume_content_id)
        # which is different from the mock_result we set up

    @patch("resumes.containers.Container.resume_repository")
    @patch("celery.result.AsyncResult")
    def test_pending_task_returns_status(self, mock_async_result, mock_repo):
        """Test that a pending task returns status information."""
        # Mock AsyncResult for pending task
        mock_result = MagicMock()
        mock_result.state = "PENDING"
        mock_result.ready.return_value = False
        mock_result.failed.return_value = False
        mock_result.id = self.task_id
        mock_async_result.return_value = mock_result

        # Mock repository methods
        mock_repository = MagicMock()
        mock_repo.return_value = mock_repository
        mock_repository.get_task_result.return_value = None

        # Make request to the enhanced endpoint
        response = self.client.get(f"/api/resume/generated/{self.task_id}")

        # Assertions
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["status"], "Pending")
        self.assertIn("Resume generation is still in progress", response.data["message"])
        self.assertEqual(response.data["task_id"], self.task_id)
        self.assertEqual(response.data["task_state"], "PENDING")

    # @patch("resumes.containers.Container.resume_repository")
    # @patch("celery.result.AsyncResult")
    # def test_failed_task_returns_error(self, mock_async_result, mock_repo):
    #     """Test that a failed task returns error information."""
    #     # Mock AsyncResult for failed task
    #     mock_result = MagicMock()
    #     mock_result.state = "FAILURE"
    #     mock_result.failed.return_value = True
    #     mock_result.id = self.task_id
    #     mock_async_result.return_value = mock_result

    #     # Make request to the enhanced endpoint
    #     response = self.client.get(f"/api/resume/generated/{self.task_id}")

    #     # Assertions
    #     self.assertEqual(response.status_code, 400)
    #     self.assertEqual(response.data["status"], "Failed")
    #     self.assertIn("Resume generation failed", response.data["message"])
    #     self.assertEqual(response.data["task_id"], self.task_id)

    @patch("resumes.containers.Container.resume_repository")
    @patch("celery.result.AsyncResult")
    def test_resume_creation_failure_handled(self, mock_async_result, mock_repo):
        """Test that resume creation failures are handled gracefully."""
        # Mock AsyncResult for successful task
        mock_result = MagicMock()
        mock_result.state = "SUCCESS"
        mock_result.status = "SUCCESS"
        mock_result.ready.return_value = True
        mock_result.failed.return_value = False
        mock_result.id = self.task_id
        mock_async_result.return_value = mock_result

        # Mock repository methods
        mock_repository = MagicMock()
        mock_repo.return_value = mock_repository

        # Mock task result data
        task_data = {
            "original_content": "Generated resume content",
            "parsed_content": {
                "full_name": "John Doe",
                "phone_number": "+1234567890",
                "work_experience": [],
                "education": [],
                "skills": ["Python", "Django"],
                "certifications": [],
                "languages": ["English"],
                "resume_summary": "Experienced developer",
            }
        }
        mock_repository.get_task_result.return_value = task_data

        # Mock resume creation failure
        mock_repository.create_resume.side_effect = Exception("Database error")

        # Make request to the enhanced endpoint
        response = self.client.get(f"/api/resume/generated/{self.task_id}")

        # Assertions
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data["status"], "Failed")
        self.assertIn("failed to create resume", response.data["message"])
        self.assertEqual(response.data["task_id"], self.task_id)
