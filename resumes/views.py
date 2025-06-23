# File: resumes/views.py
# Author: Oluwatobiloba Light
"""Resume views"""

import logging

from django.http import Http404
from rest_framework import permissions, status
from rest_framework.generics import CreateAPIView, UpdateAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from celery.exceptions import BackendError
from celery.result import AsyncResult

from resumes.containers import Container
from resumes.models import Resume
from resumes.serializers import (
    CreateResumeSerializer,
    ResumeSerializer,
    UpdateResumeSerializer,
)
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
    """Enhanced endpoint that checks task status and automatically creates resume when ready"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, resume_content_id):
        """
        Enhanced endpoint that:
        1. Checks the status of the async task
        2. If task is complete and successful, automatically creates the resume and returns it
        3. If task is still pending/running, returns status information
        4. If task failed, returns error information
        """
        resume_repo = Container.resume_repository()

        try:
            resume_content_result = AsyncResult(resume_content_id)

            # Handle failed tasks
            if (
                resume_content_result.state.lower() == "failure"
                or resume_content_result.failed()
            ):
                logger.error(f"Task {resume_content_id} failed")
                return Response(
                    {
                        "status": "Failed",
                        "message": "Resume generation failed. Please try again.",
                        "task_id": resume_content_id,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Handle completed tasks
            if resume_content_result.ready():
                cached_data = resume_repo.get_task_result(resume_content_result.id)

                # If data is not cached but task is successful, cache it first
                if (
                    cached_data is None
                    and resume_content_result.status.lower() == "success"
                ):
                    resume_repo.save_task_result(
                        resume_content_result.id,
                        resume_content_result.result,
                    )
                    cached_data = resume_content_result.result

                # If we have the task data, automatically create the resume
                if cached_data and resume_content_result.status.lower() == "success":
                    try:
                        # Create the resume automatically
                        resume = resume_repo.create_resume(
                            cached_data["original_content"],
                            cached_data["parsed_content"],
                            self.request.user,
                        )

                        # Clean up the cached data and task result
                        resume_repo.delete_task(resume_content_id)
                        resume_content_result.forget()

                        logger.info(f"Resume created successfully with ID: {resume.id}")

                        # Return the created resume data (same format as ResumeCreateView)
                        return Response(
                            {
                                "status": "Success",
                                "message": "Resume created successfully",
                                "resume": {
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
                                "task_id": resume_content_id,
                            },
                            status=status.HTTP_201_CREATED,
                        )
                    except Exception as e:
                        logger.error(f"Failed to create resume: {e}")
                        return Response(
                            {
                                "status": "Failed",
                                "message": "Resume generation completed but failed to create resume. Please try again.",
                                "task_id": resume_content_id,
                            },
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        )

                # If task completed but no valid data
                logger.error(f"Task {resume_content_id} completed but no valid data found")
                return Response(
                    {
                        "status": "Failed",
                        "message": "Resume generation completed but no valid data found. Please try again.",
                        "task_id": resume_content_id,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Handle pending tasks
            cached_data = resume_repo.get_task_result(resume_content_result.id)

            if cached_data:
                # Task is complete but AsyncResult might not reflect it yet
                try:
                    resume = resume_repo.create_resume(
                        cached_data["original_content"],
                        cached_data["parsed_content"],
                        self.request.user,
                    )

                    # Clean up the cached data
                    resume_repo.delete_task(resume_content_id)
                    resume_content_result.forget()

                    logger.info(f"Resume created successfully with ID: {resume.id}")

                    return Response(
                        {
                            "status": "Success",
                            "message": "Resume created successfully",
                            "resume": {
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
                            "task_id": resume_content_id,
                        },
                        status=status.HTTP_201_CREATED,
                    )
                except Exception as e:
                    logger.error(f"Failed to create resume from cached data: {e}")
                    return Response(
                        {
                            "status": "Failed",
                            "message": "Resume generation completed but failed to create resume. Please try again.",
                            "task_id": resume_content_id,
                        },
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

            # Task is still pending
            logger.info(f"Task {resume_content_id} is still pending")
            return Response(
                {
                    "status": "Pending",
                    "message": "Resume generation is still in progress. Please check again in a few moments.",
                    "task_id": resume_content_id,
                    "task_state": resume_content_result.state,
                },
                status=status.HTTP_202_ACCEPTED,
            )

        except BackendError:  # Raised when result backend can't find the task
            logger.error(
                f"Task result for {resume_content_id} has been deleted or doesn't exist."
            )
            return Response(
                {
                    "status": "Failed",
                    "message": "Task not found. Please generate content again.",
                    "task_id": resume_content_id,
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except KeyError:  # Raised if task metadata is missing in Redis
            logger.error(f"Task {resume_content_id} not found in the backend.")
            try:
                resume_content_result.forget()
            except:
                pass
            return Response(
                {
                    "status": "Failed",
                    "message": "Task metadata missing. Please generate content again.",
                    "task_id": resume_content_id,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:  # Catch any unexpected errors
            logger.error(f"An unexpected error occurred: {e}")
            try:
                AsyncResult(resume_content_id).revoke()
                AsyncResult(resume_content_id).forget()
            except:
                pass

            return Response(
                {
                    "status": "Failed",
                    "message": "An unexpected error occurred. Please generate content again.",
                    "task_id": resume_content_id,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
    """Enhanced endpoint that checks task status and automatically updates resume when ready"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, resume_content_id):
        """
        Enhanced endpoint that:
        1. Checks the status of the async update task
        2. If task is complete and successful, automatically updates the existing resume and returns it
        3. If task is still pending/running, returns status information
        4. If task failed, returns error information
        """
        resume_repo = Container.resume_repository()

        try:
            resume_content_result = AsyncResult(resume_content_id)

            # Handle failed tasks
            if (
                resume_content_result.state.lower() == "failure"
                or resume_content_result.failed()
            ):
                logger.error(f"Update task {resume_content_id} failed")
                return Response(
                    {
                        "status": "Failed",
                        "message": "Resume update failed. Please try again.",
                        "task_id": resume_content_id,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Handle completed tasks
            if resume_content_result.ready():
                cached_data = resume_repo.get_task_result(resume_content_result.id)

                # If data is not cached but task is successful, cache it first
                if (
                    cached_data is None
                    and resume_content_result.status.lower() == "success"
                ):
                    resume_repo.save_task_result(
                        resume_content_result.id,
                        resume_content_result.result,
                    )
                    cached_data = resume_content_result.result

                # If we have the task data, automatically update the resume
                if cached_data and resume_content_result.status.lower() == "success":
                    try:
                        resume_id = cached_data.get("resume_id")
                        if not resume_id:
                            logger.error(f"No resume_id found in task result for {resume_content_id}")
                            return Response(
                                {
                                    "status": "Failed",
                                    "message": "Resume update completed but resume ID missing. Please try again.",
                                    "task_id": resume_content_id,
                                },
                                status=status.HTTP_400_BAD_REQUEST,
                            )

                        # Update the existing resume automatically
                        update_success = resume_repo.update_resume(
                            resume_id,
                            cached_data["original_content"],
                            cached_data["parsed_content"],
                            self.request.user,
                        )

                        if update_success:
                            # Get the updated resume to return
                            try:
                                updated_resume = Resume.objects.get(id=resume_id, user=self.request.user)

                                # Clean up the cached data and task result
                                resume_repo.delete_task(resume_content_id)
                                resume_content_result.forget()

                                logger.info(f"Resume updated successfully with ID: {updated_resume.id}")

                                # Return the updated resume data (same format as UpdateAIResumeView)
                                return Response(
                                    {
                                        "status": "Success",
                                        "message": "Resume updated successfully",
                                        "resume": {
                                            "id": updated_resume.id,
                                            "first_name": updated_resume.first_name,
                                            "last_name": updated_resume.last_name,
                                            "email": updated_resume.email,
                                            "phone_number": updated_resume.phone_number,
                                            "work_experience": updated_resume.work_experience,
                                            "education": updated_resume.education,
                                            "skills": updated_resume.skills,
                                            "certifications": updated_resume.certifications,
                                            "languages": updated_resume.languages,
                                            "resume_summary": updated_resume.resume_summary,
                                        },
                                        "task_id": resume_content_id,
                                    },
                                    status=status.HTTP_200_OK,
                                )
                            except Resume.DoesNotExist:
                                logger.error(f"Resume with ID {resume_id} not found for user {self.request.user.id}")
                                return Response(
                                    {
                                        "status": "Failed",
                                        "message": "Resume not found. Please ensure you have permission to update this resume.",
                                        "task_id": resume_content_id,
                                    },
                                    status=status.HTTP_404_NOT_FOUND,
                                )
                        else:
                            logger.error(f"Failed to update resume with ID {resume_id}")
                            return Response(
                                {
                                    "status": "Failed",
                                    "message": "Resume update completed but failed to save changes. Please try again.",
                                    "task_id": resume_content_id,
                                },
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            )
                    except Exception as e:
                        logger.error(f"Failed to update resume: {e}")
                        return Response(
                            {
                                "status": "Failed",
                                "message": "Resume update completed but failed to update resume. Please try again.",
                                "task_id": resume_content_id,
                            },
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        )

                # If task completed but no valid data
                logger.error(f"Update task {resume_content_id} completed but no valid data found")
                return Response(
                    {
                        "status": "Failed",
                        "message": "Resume update completed but no valid data found. Please try again.",
                        "task_id": resume_content_id,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Handle pending tasks
            cached_data = resume_repo.get_task_result(resume_content_result.id)

            if cached_data:
                # Task is complete but AsyncResult might not reflect it yet
                try:
                    resume_id = cached_data.get("resume_id")
                    if resume_id:
                        update_success = resume_repo.update_resume(
                            resume_id,
                            cached_data["original_content"],
                            cached_data["parsed_content"],
                            self.request.user,
                        )

                        if update_success:
                            updated_resume = Resume.objects.get(id=resume_id, user=self.request.user)

                            # Clean up the cached data
                            resume_repo.delete_task(resume_content_id)
                            resume_content_result.forget()

                            logger.info(f"Resume updated successfully with ID: {updated_resume.id}")

                            return Response(
                                {
                                    "status": "Success",
                                    "message": "Resume updated successfully",
                                    "resume": {
                                        "id": updated_resume.id,
                                        "first_name": updated_resume.first_name,
                                        "last_name": updated_resume.last_name,
                                        "email": updated_resume.email,
                                        "phone_number": updated_resume.phone_number,
                                        "work_experience": updated_resume.work_experience,
                                        "education": updated_resume.education,
                                        "skills": updated_resume.skills,
                                        "certifications": updated_resume.certifications,
                                        "languages": updated_resume.languages,
                                        "resume_summary": updated_resume.resume_summary,
                                    },
                                    "task_id": resume_content_id,
                                },
                                status=status.HTTP_200_OK,
                            )
                except Exception as e:
                    logger.error(f"Failed to update resume from cached data: {e}")
                    return Response(
                        {
                            "status": "Failed",
                            "message": "Resume update completed but failed to update resume. Please try again.",
                            "task_id": resume_content_id,
                        },
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

            # Task is still pending
            logger.info(f"Update task {resume_content_id} is still pending")
            return Response(
                {
                    "status": "Pending",
                    "message": "Resume update is still in progress. Please check again in a few moments.",
                    "task_id": resume_content_id,
                    "task_state": resume_content_result.state,
                },
                status=status.HTTP_202_ACCEPTED,
            )

        except BackendError:  # Raised when result backend can't find the task
            logger.error(
                f"Update task result for {resume_content_id} has been deleted or doesn't exist."
            )
            return Response(
                {
                    "status": "Failed",
                    "message": "Task not found. Please generate content again.",
                    "task_id": resume_content_id,
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except KeyError:  # Raised if task metadata is missing in Redis
            logger.error(f"Update task {resume_content_id} not found in the backend.")
            try:
                resume_content_result.forget()
            except:
                pass
            return Response(
                {
                    "status": "Failed",
                    "message": "Task metadata missing. Please generate content again.",
                    "task_id": resume_content_id,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:  # Catch any unexpected errors
            logger.error(f"An unexpected error occurred during resume update: {e}")
            try:
                AsyncResult(resume_content_id).revoke()
                AsyncResult(resume_content_id).forget()
            except:
                pass

            return Response(
                {
                    "status": "Failed",
                    "message": "An unexpected error occurred. Please generate content again.",
                    "task_id": resume_content_id,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
