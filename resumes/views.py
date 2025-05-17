# File: resumes/views.py
# Author: Oluwatobiloba Light
"""Resume views"""

import logging
from django.http import Http404
from rest_framework.generics import CreateAPIView, UpdateAPIView
# import json
import logging

from celery.exceptions import BackendError
from celery.result import AsyncResult

# from django.core.cache import cache
from rest_framework import permissions, status
from rest_framework.generics import CreateAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from resumes.containers import Container
from resumes.models import Resume
from resumes.serializers import (
    CreateResumeSerializer,
    ResumeSerializer,
    UpdateResumeSerializer,
)
from rest_framework import status
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import permissions
from celery.result import AsyncResult
from celery.exceptions import BackendError
from resumes.serializers import CreateResumeSerializer, ResumeSerializer

# from typing import Any, Union


from subscriptions.models import SubscriptionPlan
from users.models import User

logging.basicConfig(
    level=logging.INFO,  # Set logging level to INFO or lower
    format="%(asctime)s - %(levelname)s - %(message)s",
)  # This should be modified and be in settings.py

logger = logging.getLogger(__name__)


# generate content
class GenerateAIContentView(CreateAPIView):
    """API View for generating resume content ONLY"""

    serializer_class = ResumeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """Handles generating AI resume content"""
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            repository = Container.resume_repository()

            resume_content_id = repository.generate_resume_content(
                serializer.validated_data, self.request.user.id
            )
            return Response({"resume_content_id": resume_content_id})

        headers = self.get_success_headers(serializer.data)
        logger.error(f"Resume generation failed: {serializer.errors}")
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
            headers=headers,
        )


# view generated content
class GeneratedAIContentView(APIView):
    """Get a resume content"""

    def get(self, request, resume_content_id):
        """"""
        resume_repo = Container.resume_repository()

        try:
            resume_content_result = AsyncResult(resume_content_id)

            if (
                resume_content_result.state.lower() == "failure"
                or resume_content_result.failed()
            ):
                return resume_content_result.maybe_throw()

            if resume_content_result.ready():
                cached_data = resume_repo.get_task_result(
                    resume_content_result.id
                )

                if (
                    cached_data is None
                    and resume_content_result.status.lower() == "success"
                ):

                    resume_repo.save_task_result(
                        resume_content_result.id,
                        resume_content_result.result,
                    )

                    logger.info("Resume content retrieved successfully")
                    return Response(
                        {
                            "status": resume_content_result.status,
                            "task_id": resume_content_result.task_id,
                            **resume_repo.get_task_result(resume_content_id),
                        },
                        status=status.HTTP_200_OK,
                    )

                logger.info("Resume content retrieved successfully")
                resume_content_result.forget()
                logger.info("Resume content test result deleted successfully")

                return Response(
                    {
                        **cached_data,
                    },
                    status=status.HTTP_200_OK,
                )

            cached_data = resume_repo.get_task_result(resume_content_result.id)

            if cached_data:
                logger.info("Resume content retreived successfully")
                return Response(
                    {
                        **cached_data,
                    },
                    status=status.HTTP_200_OK,
                )

            logger.error("Content is pending or has been deleted")

            logger.error(resume_content_result.state)
            return Response(
                {"status": "PENDING OR DELETED"},
                status=status.HTTP_202_ACCEPTED,
            )
        except BackendError:  # Raised when result backend can't find the task
            logger.error(
                f"Task result for {resume_content_id} has been deleted or"
                f" doesn't exist."
            )
        except KeyError:  # Raised if task metadata is missing in Redis
            logger.error(f"Task {resume_content_id} not found in the backend.")
            resume_content_result.forget()
            return Response(
                {
                    "status": "Failed",
                    "message": "Please generate content again.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:  # Catch any unexpected errors
            logger.error(f"An error occurred: {e}")
            AsyncResult(resume_content_id).revoke()
            AsyncResult(resume_content_id).forget()

            return Response(
                {
                    "status": "Failed",
                    "message": "Please generate content again!",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


# create generated content
class ResumeCreateView(CreateAPIView):
    """
    API view for creating a resume.


    """

    serializer_class = CreateResumeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer: CreateResumeSerializer):
        """
        Automatically associate the resume with the logged-in user.
        """
        serializer.save(user=self.request.user)

    def create(self, request: Request, *args, **kwargs):
        """
        Handle resume creation and logging.
        """
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            repository = Container.resume_repository()

            data = repository.get_task_result(
                request.data.get("resume_task_id")
            )

            if data:
                resume = repository.create_resume(
                    data["original_content"],
                    data["parsed_content"],
                    self.request.user,
                )

                # delete the cached resume after creation
                repository.delete_task(request.data.get("resume_task_id"))
                AsyncResult(request.data.get("resume_task_id")).forget()

                return Response(
                    {
                        "id": resume.id,
                        "first_name": resume.first_name,
                        "last_name": resume.last_name,
                        "email": resume.email,
                        "phone_number": resume.phone_number,
                        "work_experience": resume.work_experience,
                        "education": resume.education,
                        "skills": resume.skills,
                        "certifications": resume.certifications,
                        "languages": resume.languages,
                        "resume_summary": resume.resume_summary,
                    },
                    status=status.HTTP_200_OK,
                )

            headers = self.get_success_headers(serializer.data)
            logger.error(f"Resume creation failed: {serializer.errors}")
            return Response(
                {
                    "details": "Resume failed to create! Generate resume and try again"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        headers = self.get_success_headers(serializer.data)
        logger.error(f"Registration failed: {serializer.errors}")
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
            headers=headers,
        )


# Update views
class ResumeUpdateView(UpdateAPIView):
    """API VIEW TO UPDATE RESUME (NO AI GENERATION)"""

    serializer_class = ResumeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """Ensure users can only update their own resume."""
        try:
            return Resume.objects.get(
                id=self.kwargs["resume_id"], user=self.request.user
            )
        except Resume.DoesNotExist as e:
            raise Http404("Resume not found")

    def update(self, request, *args, **kwargs):

        response = super().update(request, *args, **kwargs)

        return response


# generate updated content
class UpdateGenerateAIContentView(CreateAPIView):
    """API View for generating resume content"""

    serializer_class = ResumeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, resume_id):
        """Ensure users can only update their own resume."""
        return Resume.objects.get(id=resume_id, user=self.request.user)

    def get_subscription(self):
        """Get a user's subcription"""
        return SubscriptionPlan.objects.get(user=self.request.user)

    def create(self, request, resume_id, *args, **kwargs):
        """Handles generating AI resume content"""
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            try:
                repository = Container.resume_repository()
                resume = self.get_object(resume_id)

                user = request.user
                subscription = self.get_subscription()

                if not subscription:
                    return Response(
                        {"detail": "Subscription not found."},
                        status=status.HTTP_403_FORBIDDEN,
                    )

                # if not subscription.can_generate_resume():
                #     return Response({
                #         "detail": "Free tier limit reached. Upgrade to Pro for unlimited access."
                #     }, status=status.HTTP_402_PAYMENT_REQUIRED)

                if resume.update_generate_content_count >= 3:
                    return Response(
                        {
                            "error": "You have reached your free limit. Upgrade your plan to continue"
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                resume_content_id = repository.update_resume_content(
                    resume_id, serializer.validated_data, self.request.user.id
                )
                return Response({"resume_content_id": resume_content_id})
            except:
                headers = self.get_success_headers(serializer.data)
                logger.error(f"Resume generation failed: {serializer.errors}")
                return Response(
                    serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST,
                    headers=headers,
                )


# view updated generated content
class UpdatedGeneratedAIContentView(APIView):
    """Get a resume content"""

    def get(self, request, resume_content_id):
        """"""
        resume_repo = Container.resume_repository()

        try:
            resume_content_result = AsyncResult(resume_content_id)

            if (
                resume_content_result.state.lower() == "failure"
                or resume_content_result.failed()
            ):
                return resume_content_result.maybe_throw()

            if resume_content_result.ready():
                cached_data = resume_repo.get_task_result(resume_content_result.id)

                if (
                    cached_data is None
                    and resume_content_result.status.lower() == "success"
                ):

                    resume_repo.save_task_result(
                        resume_content_result.id,
                        resume_content_result.result,
                    )

                    logger.info(f"Resume content retreived successfully")
                    return Response(
                        {
                            "status": resume_content_result.status,
                            "task_id": resume_content_result.task_id,
                            **resume_repo.get_task_result(resume_content_id),
                        },
                        status=status.HTTP_200_OK,
                    )

                logger.info(f"Resume content retreived successfully")
                resume_content_result.forget()
                logger.info(f"Resume content tast result deleted successfully")

                return Response(
                    {
                        **cached_data,
                    },
                    status=status.HTTP_200_OK,
                )

            cached_data = resume_repo.get_task_result(resume_content_result.id)

            if cached_data:
                logger.info(f"Resume content retreived successfully")
                return Response(
                    {
                        **cached_data,
                    },
                    status=status.HTTP_200_OK,
                )

            logger.error("Content is pending or has been deleted")

            print(resume_content_result.state)
            return Response(
                {"status": "PENDING OR DELETED"},
                status=status.HTTP_202_ACCEPTED,
            )
        except BackendError:  # Raised when result backend can't find the task
            print(
                f"Task result for {resume_content_id} has been deleted or doesn't exist."
            )
        except KeyError:  # Raised if task metadata is missing in Redis
            logger.error(f"Task {resume_content_id} not found in the backend.")
            resume_content_result.forget()
            return Response(
                {"status": "Failed", "message": "Please generate content again."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:  # Catch any unexpected errors
            logger.error(f"An error occurred: {e}")
            AsyncResult(resume_content_id).revoke()
            AsyncResult(resume_content_id).forget()

            return Response(
                {"status": "Failed", "message": "Please generate content again!"},
                status=status.HTTP_400_BAD_REQUEST,
            )


# update resume with generated content
class UpdateAIResumeView(UpdateAPIView):
    """API VIEW TO UPDATE RESUME BASED ON AI GENERATION"""

    serializer_class = UpdateResumeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, resume_id):
        """Ensure users can only update their own resume."""
        return Resume.objects.get(id=resume_id, user=self.request.user)

    def patch(self, request: Request, resume_task_id, *args, **kwargs):
        resume = self.get_object(request.data.get("resume_id"))
        serializer = self.serializer_class(data=request.data)
        repository = Container.resume_repository()
        data = repository.get_task_result(resume_task_id)
        parsed_data: dict | None = data["parsed_content"] if data else None

        if parsed_data:
            update_resume = repository.update_resume(
                serializer.initial_data["resume_id"],
                data["original_content"],
                parsed_data,
                self.request.user,
            )

            if update_resume:
                resume.refresh_from_db()

            # delete the cached resume after creation
            repository.delete_task(resume_task_id)
            AsyncResult(resume_task_id).forget()
            resume.save(update_fields=["update_generate_content_count"])

            return Response(
                {
                    "id": resume.id,
                    "first_name": resume.first_name,
                    "last_name": resume.last_name,
                    "email": resume.email,
                    "phone_number": resume.phone_number,
                    "work_experience": resume.work_experience,
                    "education": resume.education,
                    "skills": resume.skills,
                    "certifications": resume.certifications,
                    "languages": resume.languages,
                    "resume_summary": resume.resume_summary,
                },
                status=status.HTTP_200_OK,
            )

        logger.error(f"Resume update failed: ")
        return Response(
            {
                "details": "Resume failed to update! Update then generate resume and try again"
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


# results
class ResumeResultView(APIView):
    """RESUME API VIEW"""

    def get(self, request, resume_id):
        """Get a resume based on id"""
        try:
            resume = Resume.objects.get(id=resume_id, user=self.request.user.id)
            serializer = ResumeSerializer(resume)
            return Response({"resume": serializer.data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"resume": serializer.data}, status=status.HTTP_200_OK
            )
        except Exception:
            return Response(
                {"error": "Resume not found"}, status=status.HTTP_404_NOT_FOUND
            )
