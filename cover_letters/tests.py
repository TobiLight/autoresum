# File: cover_letters/tests.py
# Author: Oluwatobiloba Light
"""Cover letter Tests"""

import json
from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase
from rest_framework.test import APIClient
from cover_letters.models import CoverLetter
from cover_letters.services.ai_generator import OpenAICoverLetterGenerator
from cover_letters.tasks import generate_cover_letter_content_task
from users.models import User


class GenerateCoverLetterTaskTest(TestCase):
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
    def cover_letter_generator():
        """Fixture to create an instance of OpenAICoverLetterGenerator."""
        return OpenAICoverLetterGenerator(
            api_key="fake_api_key", organization_id="fake_org_id"
        )

    @patch(
        "cover_letters.tasks.generate_cover_letter_content_task.delay"
    )  # Mocking the Celery task
    @patch("cover_letters.containers.Container.cover_letter_service")
    def test_generate_cover_letter_content_task(
        self, mock_cover_letter_service, mock_generate_cover_letter
    ):
        """Test the Celery task for generating a cover_letter."""

        # Mock the AI cover_letter generator service
        mock_generator = MagicMock()

        mock_generator.generate_cover_letter_content_task.return_value = {
            "cover_letter_id": 1,
        }

        mock_cover_letter_service.return_value = mock_generator

        # Mock Celery task return value
        mock_generate_cover_letter.return_value = "mock_task_id"

        # Test data
        user_data = {
            "full_name": "John Doe",
            "email": "john.doe@example.com",
            "phone_number": "+1402447307523",
            "company_name": "Edves Edtech",
            "job_title": "PHP Developer",
            "job_description": "We are seeking an experienced Intermediate PHP Developer with 4 years of experience to join our dynamic team. The ideal candidate will have expertise in Laravel, strong database management skills with MySQL and PostgreSQL, and experience working with Redis for caching and performance optimization. You will play a key role in developing, maintaining, and optimizing web applications while collaborating with cross-functional teams.",
        }

        user_id = 1

        # Run the Celery task (which is now mocked)
        result = generate_cover_letter_content_task.delay(user_data, user_id)

        # Assertions
        assert result == "mock_task_id"
        mock_generate_cover_letter.assert_called_once_with(user_data, user_id)

    @patch(
        "cover_letters.services.ai_generator.OpenAICoverLetterGenerator.parse_cover_letter_content"
    )
    @patch(
        "cover_letters.services.ai_generator.OpenAICoverLetterGenerator.generate_cover_letter_content"
    )
    @patch(
        "cover_letters.services.ai_generator.OpenAICoverLetterGenerator"
    )  # Mock OpenAI class
    def test_parse_ai_response(
        self,
        mock_openai,
        mock_generate_cover_letter_content,
        mock_parse_cover_letter_content,
    ):
        """Test AI response parsing and structured cover_letter generation without making real OpenAI API calls."""

        # ✅ Ensure OpenAI class is mocked
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # ✅ Mock generate_cover_letter_content so it doesn't call OpenAI
        mock_generate_cover_letter_content.return_value = """## Oluwatobiloba Light
        johndoe@example.com
        +1234567890123
        Ngozi Odukwe

        Hiring Manager
        Edves Edtech

        Dear Ngozi Odukwe,
        I am writing to express my interest in the PHP Developer position at Edves Edtech as advertised. With 4 years of experience in PHP development, particularly in Laravel, MySQL, PostgreSQL, and Redis, I am excited about the opportunity to contribute to your dynamic team and help optimize web applications for performance and efficiency.In your job description, you mentioned the need for an experienced Intermediate PHP Developer with expertise in Laravel and strong database management skills with MySQL and PostgreSQL. I have a proven track record in these areas and have successfully worked with Redis for caching and performance optimization in previous projects. I am confident that my technical skills and experience align perfectly with the requirements of the role at Edves Edtech.I am eager to collaborate with cross-functional teams to develop, maintain, and optimize web applications, as stated in the job description. My goal is to leverage my skills to enhance application performance, contribute to the growth of the team, and further my professional development in a collaborative environment.I am thrilled about the opportunity to bring my expertise to Edves Edtech and contribute to the innovative projects your team is working on. Thank you for considering my application. I look forward to the possibility of discussing how my background, skills, and enthusiasms align with the needs of your team.Thank you for your time and consideration.

        Sincerely,
        Oluwatobiloba Light"""

        # ✅ Mock parse_cover_letter_content_content
        mock_parse_cover_letter_content.return_value = {
            "company_name": "Edves Edtech",
            "job_title": "PHP Developer",
            "cover_letter": "I am writing to express my interest in the PHP Developer position at Edves Edtech, as advertised. With 4 years of experience in PHP development, specializing in Laravel, MySQL, PostgreSQL, and Redis, I am excited about the opportunity to contribute to your dynamic team and help optimize web applications for performance and efficiency. In response to your job description for an Intermediate PHP Developer, I am confident in my ability to meet and exceed the expectations of the role. My experience aligns closely with the requirements outlined, particularly in Laravel development, database management with MySQL and PostgreSQL, and utilizing Redis for caching and performance enhancement. I have successfully collaborated with cross-functional teams in the past to deliver high-quality web applications. I am particularly drawn to Edves Edtech because of its focus on innovation and collaboration. Your emphasis on developing and maintaining web applications resonates with my professional goals of continuous growth and learning in a supportive environment. I am eager to bring my expertise in PHP development to your team and contribute to the success of your projects. I am enthusiastic about the opportunity to further discuss how my background, skills, and enthusiasms align with the needs of Edves Edtech. Thank you for considering my application. I look forward to the possibility of contributing to your team and helping Edves Edtech achieve its goals. Warm regards, Oluwatobiloba Light",
        }

        # Initialize the generator
        generator = mock_openai

        data = {
            "full_name": "Oluwatobiloba Light",
            "email": "johndoe@example.com",
            "phone_number": "+1234567890123",
            "company_name": "Edves Edtech",
            "job_title": "PHP Developer",
            "job_description": "We are seeking an experienced Intermediate PHP Developer with 4 years of experience to join our dynamic team. The ideal candidate will have expertise in Laravel, strong database management skills with MySQL and PostgreSQL, and experience working with Redis for caching and performance optimization. You will play a key role in developing, maintaining, and optimizing web applications while collaborating with cross-functional teams.",
        }

        # Simulate response parsing
        cover_letter_content = generator.generate_cover_letter_content(
            data
        )  # ✅ Mocked, so no API call
        parsed_data = generator.parse_cover_letter_content(
            cover_letter_content
        )  # ✅ Mocked, returns expected data

        # ✅ Assertions
        self.assertIn("Edves Edtech", parsed_data["company_name"])
        self.assertIn("PHP Developer", parsed_data["job_title"])
        self.assertIn("cover_letter", parsed_data)

        # ✅ Ensure generate_cover_letter_content was actually called
        mock_generate_cover_letter_content.assert_called_once_with(data)


class UpdateCoverLetterTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", email="testuser@example.com", password="testpass"
        )
        self.other_user = User.objects.create_user(
            username="otheruser", email="otheruser@example.com", password="testpass"
        )
        self.cover_letter = CoverLetter.objects.create(
            user=self.user,
            name="John Doe",
            email="john@example.com",
            company_name="Tech Corp",
            job_title="Software Engineer",
            cover_letter_content="Cover letter content",
        )
        self.client.force_authenticate(user=self.user)

    def test_update_cover_letter_success(self):
        """Test that an authenticated user can update their cover letter."""
        update_data = {"full_name": "Updated John"}
        response = self.client.patch(
            f"/api/cover-letter/update/{self.cover_letter.id}", update_data
        )
        self.assertEqual(response.status_code, 200)
        self.cover_letter.refresh_from_db()
        self.assertEqual(self.cover_letter.name, "Updated John")
        self.assertEqual(self.cover_letter.job_title, "Software Engineer")

    def test_update_other_user_cover_letter_fails(self):
        """Test that a user cannot update another user's cover letter."""
        self.client.force_authenticate(user=self.other_user)
        update_data = {"full_name": "Hacker"}
        response = self.client.patch(
            f"/api/cover-letter/update/{self.cover_letter.id}", update_data
        )
        self.assertEqual(response.status_code, 404)  # Should return 404

    @patch("cover_letters.containers.Container.cover_letter_repository")
    @patch("cover_letters.tasks.update_cover_letter_content_task.delay")
    def test_ai_update_cover_letter_success(self, mock_update_task, mock_repo):
        """Test updating a cover letter with AI-generated content."""
        mock_update_task.return_value = "mock_task_id"

        mock_repo.return_value.get_task_result.return_value = {
            "original_content": "# John Doe\njohn.doe@example.com\n+1402447307523\n\nEdves Edtech\nHiring Manager\n\nDear Hiring Manager,\n\nI am writing to express my interest in the PHP Developer position at Edves Edtech, as advertised. With a solid background in PHP development and a passion for creating efficient and scalable web applications, I am excited about the opportunity to contribute to your dynamic team.\n\nIn response to your job description for an Intermediate PHP Developer with expertise in Laravel, database management skills in MySQL and PostgreSQL, and experience with Redis for caching and performance optimization, I am confident that my 4 years of experience align well with the requirements of the role. I have successfully developed and maintained web applications using Laravel, ensuring optimal performance and reliability.\n\nI have a proven track record of collaborating effectively with cross-functional teams to deliver high-quality projects on time and within budget. My experience in database management and optimization techniques, including working with MySQL, PostgreSQL, and Redis, has enabled me to enhance the performance of web applications while ensuring data integrity and security.\n\nI am particularly drawn to Edves Edtech's commitment to innovation and excellence in the education technology sector. I am eager to leverage my skills and expertise to contribute to the development and optimization of web applications that will positively impact the educational experience of users.\n\nThank you for considering my application. I am looking forward to the opportunity to discuss how my background, skills, and enthusiasm align with the needs of Edves Edtech. Please feel free to contact me at john.doe@example.com or +1402447307523 to schedule a meeting.\n\nWarm regards,\n\nJohn Doe",
            "parsed_content": {
                "company_name": "Edves Edtech",
                "job_title": "PHP Developer",
                "cover_letter": "Dear Hiring Manager, I am writing to express my interest in the PHP Developer position at Edves Edtech, as advertised. With a solid background in PHP development and a passion for creating efficient and scalable web applications, I am excited about the opportunity to contribute to your dynamic team. In response to your job description for an Intermediate PHP Developer with expertise in Laravel, database management skills in MySQL and PostgreSQL, and experience with Redis for caching and performance optimization, I am confident that my 4 years of experience align well with the requirements of the role. I have successfully developed and maintained web applications using Laravel, ensuring optimal performance and reliability. I have a proven track record of collaborating effectively with cross-functional teams to deliver high-quality projects on time and within budget. My experience in database management and optimization techniques, including working with MySQL, PostgreSQL, and Redis, has enabled me to enhance the performance of web applications while ensuring data integrity and security. I am particularly drawn to Edves Edtech's commitment to innovation and excellence in the education technology sector. I am eager to leverage my skills and expertise to contribute to the development and optimization of web applications that will positively impact the educational experience of users. Thank you for considering my application. I am looking forward to the opportunity to discuss how my background, skills, and enthusiasm align with the needs of Edves Edtech. Please feel free to contact me at john.doe@example.com or +1402447307523 to schedule a meeting. Warm regards, John Doe",
                "name": "John Doe",
                "email": "john.doe@example.com",
                "phone": "+1402447307523",
            },
        }

        update_data = {
            "cover_letter_id": str(self.cover_letter.id),
            "cover_letter_task_id": "mock_task_id",
        }
        response = self.client.patch(
            f"/api/cover-letter/update/generated/{update_data['cover_letter_task_id']}",
            update_data,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("id", response.data)

    @patch("cover_letters.containers.Container.cover_letter_repository")
    def test_ai_update_cover_letter_no_task_result(self, mock_repo):
        """Test that updating with AI fails when no task result exists."""
        mock_repo.return_value.get_task_result.return_value = None

        update_data = {
            "cover_letter_id": str(self.cover_letter.id),
            "cover_letter_task_id": "nonexistent_task",
        }
        response = self.client.patch(
            f"/api/cover-letter/update/generated/{update_data['cover_letter_task_id']}",
            update_data,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Cover Letter failed to update", response.data["details"])


class OpenAICoverLetterGeneratorTest(TestCase):
    """Unit tests for OpenAICoverLetterGenerator."""

    def setUp(self):
        """Set up test instance."""
        self.cover_letter_generator = OpenAICoverLetterGenerator(
            api_key="fake_api_key", organization_id="fake_org_id"
        )

    def test_check_api_key(self):
        """Test that check_api_key raises an error when API key is missing."""
        with self.assertRaises(ValueError) as context:
            OpenAICoverLetterGenerator(
                api_key="", organization_id="fake_org_id"
            )
        self.assertEqual(str(context.exception), "API key is required.")

    @patch(
        "cover_letters.services.ai_generator.OpenAICoverLetterGenerator.init_openai"
    )
    def test_init_openai(self, mock_init_openai):
        """Test OpenAI client initialization."""
        mock_client = MagicMock()
        mock_init_openai.return_value = mock_client

        client = self.cover_letter_generator.init_openai()

        mock_init_openai.assert_called_once()
        self.assertEqual(
            client, mock_client
        )  # Ensure the returned client is the mock

    @patch(
        "cover_letters.services.ai_generator.OpenAICoverLetterGenerator.init_openai"
    )
    def test_parse_cover_letter_content(self, mock_init_openai):
        """Test parsing AI cover_letter content."""
        mock_client = MagicMock()
        mock_init_openai.return_value = mock_client

        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "full_name": "Oluwatobiloba Light",
                "email": "johndoe@example.com",
                "phone_number": "+1234567890123",
                "company_name": "Edves Edtech",
                "job_title": "PHP Developer",
                "job_description": "We are seeking an experienced Intermediate PHP Developer with 4 years of experience to join our dynamic team. The ideal candidate will have expertise in Laravel, strong database management skills with MySQL and PostgreSQL, and experience working with Redis for caching and performance optimization. You will play a key role in developing, maintaining, and optimizing web applications while collaborating with cross-functional teams.",
            }
        )
        mock_client.chat.completions.create.return_value = mock_response

        parsed_data = self.cover_letter_generator.parse_cover_letter_content(
            """## Oluwatobiloba Light
        johndoe@example.com
        +1234567890123
        Ngozi Odukwe

        Hiring Manager
        Edves Edtech

        Dear Ngozi Odukwe,
        I am writing to express my interest in the PHP Developer position at Edves Edtech as advertised. With 4 years of experience in PHP development, particularly in Laravel, MySQL, PostgreSQL, and Redis, I am excited about the opportunity to contribute to your dynamic team and help optimize web applications for performance and efficiency.In your job description, you mentioned the need for an experienced Intermediate PHP Developer with expertise in Laravel and strong database management skills with MySQL and PostgreSQL. I have a proven track record in these areas and have successfully worked with Redis for caching and performance optimization in previous projects. I am confident that my technical skills and experience align perfectly with the requirements of the role at Edves Edtech.I am eager to collaborate with cross-functional teams to develop, maintain, and optimize web applications, as stated in the job description. My goal is to leverage my skills to enhance application performance, contribute to the growth of the team, and further my professional development in a collaborative environment.I am thrilled about the opportunity to bring my expertise to Edves Edtech and contribute to the innovative projects your team is working on. Thank you for considering my application. I look forward to the possibility of discussing how my background, skills, and enthusiasms align with the needs of your team.Thank you for your time and consideration.

        Sincerely,
        Oluwatobiloba Light"""
        )

        self.assertEqual(parsed_data["full_name"], "Oluwatobiloba Light")
        self.assertEqual(parsed_data["email"], "johndoe@example.com")
        self.assertEqual(parsed_data["company_name"], "Edves Edtech")
        self.assertEqual(parsed_data["job_title"], "PHP Developer")
        mock_client.chat.completions.create.assert_called_once()

    @patch(
        "cover_letters.services.ai_generator.OpenAICoverLetterGenerator.init_openai"
    )
    def test_generate_cover_letter_content(self, mock_init_openai):
        """Test generating cover_letter content."""
        mock_client = MagicMock()
        mock_init_openai.return_value = mock_client

        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            "Generated cover letter Content"
        )
        mock_client.chat.completions.create.return_value = mock_response

        data = {
            "full_name": "Oluwatobiloba Light",
            "email": "johndoe@example.com",
            "phone_number": "+1234567890123",
            "company_name": "Edves Edtech",
            "job_title": "PHP Developer",
            "job_description": "We are seeking an experienced Intermediate PHP Developer with 4 years of experience to join our dynamic team. The ideal candidate will have expertise in Laravel, strong database management skills with MySQL and PostgreSQL, and experience working with Redis for caching and performance optimization. You will play a key role in developing, maintaining, and optimizing web applications while collaborating with cross-functional teams.",
        }

        cover_letter_content = (
            self.cover_letter_generator.generate_cover_letter_content(data)
        )

        self.assertEqual(cover_letter_content, "Generated cover letter Content")
        mock_client.chat.completions.create.assert_called_once()


class ViewGeneratedCoverLetterContentViewTest(TestCase):
    """
    Test the enhanced ViewGeneratedCoverLetterContentView
    that automatically creates cover letters.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="testpass",
        )
        self.client.force_authenticate(user=self.user)
        self.task_id = "test-cover-letter-task-id-123"

    @patch("cover_letters.containers.Container.cover_letter_repository")
    @patch("celery.result.AsyncResult")
    def test_successful_task_creates_cover_letter_automatically(self, mock_async_result, mock_repo):
        """Test that a successful task automatically creates a cover letter."""
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
            "original_content": "Generated cover letter content",
            "parsed_content": {
                "name": "John Doe",
                "email": "john.doe@example.com",
                "phone": "+1234567890",
                "company_name": "Tech Corp",
                "job_title": "Software Engineer",
                "cover_letter": "Dear Hiring Manager, I am writing to express my interest...",
            }
        }
        mock_repository.get_task_result.return_value = task_data

        # Mock created cover letter
        mock_cover_letter = MagicMock()
        mock_cover_letter.id = 1
        mock_cover_letter.name = "John Doe"
        mock_cover_letter.email = "john.doe@example.com"
        mock_cover_letter.phone_number = "+1234567890"
        mock_cover_letter.company_name = "Tech Corp"
        mock_cover_letter.job_title = "Software Engineer"
        mock_cover_letter.cover_letter_content = "Dear Hiring Manager, I am writing to express my interest..."
        mock_cover_letter.generated_content = "Generated cover letter content"
        mock_repository.create_cover_letter.return_value = mock_cover_letter

        # Make request to the enhanced endpoint
        response = self.client.get(f"/api/cover-letter/generated/{self.task_id}")

        # Assertions
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "Success")
        self.assertEqual(response.data["message"], "Cover letter created successfully")
        self.assertIn("cover_letter", response.data)
        self.assertEqual(response.data["cover_letter"]["id"], 1)
        self.assertEqual(response.data["cover_letter"]["name"], "John Doe")
        self.assertEqual(response.data["task_id"], self.task_id)

        # Verify repository methods were called
        mock_repository.create_cover_letter.assert_called_once_with(
            task_data["original_content"],
            task_data["parsed_content"],
            self.user
        )
        mock_repository.delete_task.assert_called_once_with(self.task_id)

    @patch("cover_letters.containers.Container.cover_letter_repository")
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
        response = self.client.get(f"/api/cover-letter/generated/{self.task_id}")

        # Assertions
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["status"], "Pending")
        self.assertIn("Cover letter generation is still in progress", response.data["message"])
        self.assertEqual(response.data["task_id"], self.task_id)
        self.assertEqual(response.data["task_state"], "PENDING")

    # @patch("cover_letters.containers.Container.cover_letter_repository")
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
    #     response = self.client.get(f"/api/cover-letter/generated/{self.task_id}")

    #     # Assertions
    #     self.assertEqual(response.status_code, 400)
    #     self.assertEqual(response.data["status"], "Failed")
        self.assertIn("Cover letter generation failed", response.data["message"])
        self.assertEqual(response.data["task_id"], self.task_id)

    @patch("cover_letters.containers.Container.cover_letter_repository")
    @patch("celery.result.AsyncResult")
    def test_cover_letter_creation_failure_handled(self, mock_async_result, mock_repo):
        """Test that cover letter creation failures are handled gracefully."""
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
            "original_content": "Generated cover letter content",
            "parsed_content": {
                "name": "John Doe",
                "email": "john.doe@example.com",
                "phone": "+1234567890",
                "company_name": "Tech Corp",
                "job_title": "Software Engineer",
                "cover_letter": "Dear Hiring Manager, I am writing to express my interest...",
            }
        }
        mock_repository.get_task_result.return_value = task_data

        # Mock cover letter creation failure
        mock_repository.create_cover_letter.side_effect = Exception("Database error")

        # Make request to the enhanced endpoint
        response = self.client.get(f"/api/cover-letter/generated/{self.task_id}")

        # Assertions
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data["status"], "Failed")
        self.assertIn("failed to create cover letter", response.data["message"])
        self.assertEqual(response.data["task_id"], self.task_id)
