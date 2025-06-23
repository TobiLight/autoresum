# File: cover_letters/views.py
# Author: Oluwatobiloba Light
"""Cover letter views"""

import json
import logging

from django.http import Http404
from rest_framework import permissions, status
from rest_framework.generics import CreateAPIView, UpdateAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from celery.exceptions import BackendError
from celery.result import AsyncResult

from cover_letters.containers import Container
from cover_letters.models import CoverLetter
from cover_letters.serializers import (
    CoverLetterSerializer,
    CreateCoverLetterSerializer,
    UpdateCoverLetterSerializer,
    GenerateCoverLetterSerializer,
)

logging.basicConfig(
    level=logging.INFO,  # Set logging level to INFO or lower
    format="%(asctime)s - %(levelname)s - %(message)s",
)  # This should be modified and be in settings.py

logger = logging.getLogger(__name__)


# GENERATE COVER LETTER CONTENT VIEW
class GenerateAICoverLetterContentView(CreateAPIView):
    """API VIEW TO GENERATE AI-GENERATED COVER LETTER CONTENT"""

    serializer_class = CoverLetterSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """Handles generating AI cover letter content"""
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            repository = Container.cover_letter_repository()

            cover_letter_task_id = repository.generate_cover_letter_content(
                serializer.validated_data, self.request.user.id
            )
            return Response({"cover_letter_task_id": cover_letter_task_id})
            return Response(
                {"cover_letter_content_id": cover_letter_content_id}
            )

        headers = self.get_success_headers(serializer.data)
        logger.error(f"Cover letter generation failed: {serializer.errors}")
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
            headers=headers,
        )


class ViewGeneratedCoverLetterContentView(APIView):
    """Enhanced endpoint that checks task status and automatically creates cover letter when ready"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, cover_letter_task_id):
        """
        Enhanced endpoint that:
        1. Checks the status of the async task
        2. If task is complete and successful, automatically creates the cover letter and returns it
        3. If task is still pending/running, returns status information
        4. If task failed, returns error information
        """
        cover_letter_repo = Container.cover_letter_repository()

        try:
            cover_letter_content_result = AsyncResult(cover_letter_task_id)

            # Handle failed tasks
            if (
                cover_letter_content_result.state.lower() == "failure"
                or cover_letter_content_result.failed()
            ):
                logger.error(f"Task {cover_letter_task_id} failed")
                return Response(
                    {
                        "status": "Failed",
                        "message": "Cover letter generation failed. Please try again.",
                        "task_id": cover_letter_task_id,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Handle completed tasks
            if cover_letter_content_result.ready():
                cached_data = cover_letter_repo.get_task_result(cover_letter_content_result.id)

                # If data is not cached but task is successful, cache it first
                if (
                    cached_data is None
                    and cover_letter_content_result.status.lower() == "success"
                ):
                    cover_letter_repo.save_task_result(
                        cover_letter_content_result.id,
                        cover_letter_content_result.result,
                    )
                    cached_data = cover_letter_content_result.result

                # If we have the task data, automatically create the cover letter
                if cached_data and cover_letter_content_result.status.lower() == "success":
                    try:
                        # Create the cover letter automatically
                        cover_letter = cover_letter_repo.create_cover_letter(
                            cached_data["original_content"],
                            cached_data["parsed_content"],
                            self.request.user,
                        )

                        # Clean up the cached data and task result
                        cover_letter_repo.delete_task(cover_letter_task_id)
                        cover_letter_content_result.forget()

                        logger.info(f"Cover letter created successfully with ID: {cover_letter.id}")

                        # Return the created cover letter data (same format as CoverLetterCreateView)
                        return Response(
                            {
                                "status": "Success",
                                "message": "Cover letter created successfully",
                                "cover_letter": {
                                    "id": cover_letter.id,
                                    "name": cover_letter.name,
                                    "email": cover_letter.email,
                                    "phone_number": cover_letter.phone_number,
                                    "company_name": cover_letter.company_name,
                                    "job_title": cover_letter.job_title,
                                    "cover_letter_content": cover_letter.cover_letter_content,
                                    "generated_content": cover_letter.generated_content,
                                },
                                "task_id": cover_letter_task_id,
                            },
                            status=status.HTTP_201_CREATED,
                        )
                    except Exception as e:
                        logger.error(f"Failed to create cover letter: {e}")
                        return Response(
                            {
                                "status": "Failed",
                                "message": "Cover letter generation completed but failed to create cover letter. Please try again.",
                                "task_id": cover_letter_task_id,
                            },
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        )

                # If task completed but no valid data
                logger.error(f"Task {cover_letter_task_id} completed but no valid data found")
                return Response(
                    {
                        "status": "Failed",
                        "message": "Cover letter generation completed but no valid data found. Please try again.",
                        "task_id": cover_letter_task_id,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Handle pending tasks
            cached_data = cover_letter_repo.get_task_result(cover_letter_content_result.id)

            if cached_data:
                # Task is complete but AsyncResult might not reflect it yet
                try:
                    cover_letter = cover_letter_repo.create_cover_letter(
                        cached_data["original_content"],
                        cached_data["parsed_content"],
                        self.request.user,
                    )

                    # Clean up the cached data
                    cover_letter_repo.delete_task(cover_letter_task_id)
                    cover_letter_content_result.forget()

                    logger.info(f"Cover letter created successfully with ID: {cover_letter.id}")

                    return Response(
                        {
                            "status": "Success",
                            "message": "Cover letter created successfully",
                            "cover_letter": {
                                "id": cover_letter.id,
                                "name": cover_letter.name,
                                "email": cover_letter.email,
                                "phone_number": cover_letter.phone_number,
                                "company_name": cover_letter.company_name,
                                "job_title": cover_letter.job_title,
                                "cover_letter_content": cover_letter.cover_letter_content,
                                "generated_content": cover_letter.generated_content,
                            },
                            "task_id": cover_letter_task_id,
                        },
                        status=status.HTTP_201_CREATED,
                    )
                except Exception as e:
                    logger.error(f"Failed to create cover letter from cached data: {e}")
                    return Response(
                        {
                            "status": "Failed",
                            "message": "Cover letter generation completed but failed to create cover letter. Please try again.",
                            "task_id": cover_letter_task_id,
                        },
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

            # Task is still pending
            logger.info(f"Task {cover_letter_task_id} is still pending")
            return Response(
                {
                    "status": "Pending",
                    "message": "Cover letter generation is still in progress. Please check again in a few moments.",
                    "task_id": cover_letter_task_id,
                    "task_state": cover_letter_content_result.state,
                },
                status=status.HTTP_202_ACCEPTED,
            )

        except BackendError:  # Raised when result backend can't find the task
            logger.error(
                f"Task result for {cover_letter_task_id} has been deleted or doesn't exist."
            )
            return Response(
                {
                    "status": "Failed",
                    "message": "Task not found. Please generate content again.",
                    "task_id": cover_letter_task_id,
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except KeyError:  # Raised if task metadata is missing in Redis
            logger.error(f"Task {cover_letter_task_id} not found in the backend.")
            try:
                cover_letter_content_result.forget()
            except:
                pass
            return Response(
                {
                    "status": "Failed",
                    "message": "Task metadata missing. Please generate content again.",
                    "task_id": cover_letter_task_id,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:  # Catch any unexpected errors
            logger.error(f"An unexpected error occurred: {e}")
            try:
                AsyncResult(cover_letter_task_id).revoke()
                AsyncResult(cover_letter_task_id).forget()
            except:
                pass

            return Response(
                {
                    "status": "Failed",
                    "message": "An unexpected error occurred. Please generate content again.",
                    "task_id": cover_letter_task_id,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CoverLetterCreateView(CreateAPIView):
    """
    API view for creating a Cover letter.


    """

    serializer_class = CreateCoverLetterSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer: CreateCoverLetterSerializer):
        """
        Automatically associate the cover_letter with the logged-in user.
        """
        serializer.save(user=self.request.user)

    def create(self, request: Request, *args, **kwargs):
        """
        Handle Cover letter creation and logging.
        """
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            repository = Container.cover_letter_repository()

            data = repository.get_task_result(
                request.data.get("cover_letter_task_id")
            )

            if data:
                cover_letter = repository.create_cover_letter(
                    data["original_content"],
                    data["parsed_content"],
                    self.request.user,
                )

                # delete the cached cover_letter after creation
                repository.delete_task(request.data.get("cover_letter_task_id"))
                AsyncResult(request.data.get("cover_letter_task_id")).forget()

                return Response(
                    {
                        "id": cover_letter.id,
                        "name": cover_letter.name,
                        "email": cover_letter.email,
                        "phone_number": cover_letter.phone_number,
                        "company_name": cover_letter.company_name,
                        "job_title": cover_letter.job_title,
                        "cover_letter_content": cover_letter.cover_letter_content,
                        "generated_content": cover_letter.generated_content,
                    },
                    status=status.HTTP_200_OK,
                )

            headers = self.get_success_headers(serializer.data)
            logger.error(f"Cover letter creation failed: {serializer.errors}")
            return Response(
                {
                    "details": "Cover letter failed to create! Generate cover_letter and try again"
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


# update views
# Update cover letter without generated content
class CoverLetterUpdateView(UpdateAPIView):
    """API VIEW TO UPDATE RESUME (NO AI GENERATION)"""

    serializer_class = CoverLetterSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """Ensure users can only update their own resume."""
        try:
            return CoverLetter.objects.get(
                id=self.kwargs["cover_letter_id"], user=self.request.user
            )
        except CoverLetter.DoesNotExist as e:
            raise Http404("Cover letter not found")

    def update(self, request, *args, **kwargs):

        response = super().update(request, *args, **kwargs)

        return response

# update cover letter with generated content
class UpdateAICoverLetterView(UpdateAPIView):
    """API VIEW TO UPDATE RESUME BASED ON AI GENERATION"""

    serializer_class = UpdateCoverLetterSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """Ensure users can only update their own cover letter."""
        try:
            return CoverLetter.objects.get(
                id=self.request.data.get("cover_letter_id"), user=self.request.user
            )
        except CoverLetter.DoesNotExist as e:
            raise Http404("Cover letter not found")

    def update(self, request: Request, cover_letter_task_id, *args, **kwargs):
        cover_letter = self.get_object()
        serializer = self.serializer_class(data=request.data)
        repository = Container.cover_letter_repository()
        data = repository.get_task_result(cover_letter_task_id)
        parsed_data: dict | None = data["parsed_content"] if data else None

        if parsed_data:
            update_cover_letter = repository.update_cover_letter(
                serializer.initial_data["cover_letter_id"],
                data["original_content"],
                parsed_data,
                self.request.user,
            )

            if update_cover_letter:
                cover_letter.refresh_from_db()

            # delete the cached cover_letter after creation
            repository.delete_task(cover_letter_task_id)
            AsyncResult(cover_letter_task_id).forget()
            cover_letter.save(update_fields=["update_generate_content_count"])

            return Response(
                {
                    "id": cover_letter.id,
                    "name": cover_letter.name,
                    "email": cover_letter.email,
                    "phone_number": cover_letter.phone_number,
                    "company_name": cover_letter.company_name,
                    "job_title": cover_letter.job_title,
                    "cover_letter_content": cover_letter.cover_letter_content,
                    "generated_content": cover_letter.generated_content,
                    "parsed_content": cover_letter.parsed_content,
                },
                status=status.HTTP_200_OK,
            )

        logger.error(f"Cover Letter update failed: ")
        return Response(
            {
                "details": "Cover Letter failed to update! Update then generate cover_letter and try again"
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


# generate updated content
class UpdateGenerateAICoverLetterContentView(CreateAPIView):
    """API VIEW TO GENERATE AI-GENERATED COVER LETTER CONTENT"""

    serializer_class = CoverLetterSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, cover_letter_id):
        """Ensure users can only update their own cover letter."""
        try:
            return CoverLetter.objects.get(id=cover_letter_id, user=self.request.user)
        except CoverLetter.DoesNotExist as e:
            raise Http404("Cover letter not found")

    def create(self, request, cover_letter_id, *args, **kwargs):
        """Handles generating AI cover letter content"""
        serializer = self.serializer_class(data=request.data)
        cover_letter = self.get_object(cover_letter_id)

        if serializer.is_valid():
            repository = Container.cover_letter_repository()

            if cover_letter.update_generate_content_count >= 3:
                return Response(
                    {
                        "error": "You have reached your free limit. Upgrade your plan to continue"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            cover_letter_task_id = repository.update_cover_letter_content(
                cover_letter_id, serializer.validated_data, self.request.user.id
            )
            return Response({"cover_letter_task_id": cover_letter_task_id})

        headers = self.get_success_headers(serializer.data)
        logger.error(f"Cover letter generation failed: {serializer.errors}")
        return Response(
            serializer.errors, status=status.HTTP_400_BAD_REQUEST, headers=headers
        )


# view updated generated content
class UpdatedGeneratedAICoverLetterContentView(APIView):
    """Enhanced endpoint that checks task status and automatically updates cover letter when ready"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, cover_letter_content_id):
        """
        Enhanced endpoint that:
        1. Checks the status of the async update task
        2. If task is complete and successful, automatically updates the existing cover letter and returns it
        3. If task is still pending/running, returns status information
        4. If task failed, returns error information
        """
        cover_letter_repo = Container.cover_letter_repository()

        try:
            cover_letter_content_result = AsyncResult(cover_letter_content_id)

            # Handle failed tasks
            if (
                cover_letter_content_result.state.lower() == "failure"
                or cover_letter_content_result.failed()
            ):
                logger.error(f"Update task {cover_letter_content_id} failed")
                return Response(
                    {
                        "status": "Failed",
                        "message": "Cover letter update failed. Please try again.",
                        "task_id": cover_letter_content_id,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Handle completed tasks
            if cover_letter_content_result.ready():
                cached_data = cover_letter_repo.get_task_result(cover_letter_content_result.id)

                # If data is not cached but task is successful, cache it first
                if (
                    cached_data is None
                    and cover_letter_content_result.status.lower() == "success"
                ):
                    cover_letter_repo.save_task_result(
                        cover_letter_content_result.id,
                        cover_letter_content_result.result,
                    )
                    cached_data = cover_letter_content_result.result

                # If we have the task data, automatically update the cover letter
                if cached_data and cover_letter_content_result.status.lower() == "success":
                    try:
                        cover_letter_id = cached_data.get("cover_letter_id")
                        if not cover_letter_id:
                            logger.error(f"No cover_letter_id found in task result for {cover_letter_content_id}")
                            return Response(
                                {
                                    "status": "Failed",
                                    "message": "Cover letter update completed but cover letter ID missing. Please try again.",
                                    "task_id": cover_letter_content_id,
                                },
                                status=status.HTTP_400_BAD_REQUEST,
                            )

                        # Update the existing cover letter automatically
                        update_success = cover_letter_repo.update_cover_letter(
                            cover_letter_id,
                            cached_data["original_content"],
                            cached_data["parsed_content"],
                            self.request.user,
                        )

                        if update_success:
                            # Get the updated cover letter to return
                            try:
                                updated_cover_letter = CoverLetter.objects.get(id=cover_letter_id, user=self.request.user)

                                # Clean up the cached data and task result
                                cover_letter_repo.delete_task(cover_letter_content_id)
                                cover_letter_content_result.forget()

                                logger.info(f"Cover letter updated successfully with ID: {updated_cover_letter.id}")

                                # Return the updated cover letter data (same format as UpdateAICoverLetterView)
                                return Response(
                                    {
                                        "status": "Success",
                                        "message": "Cover letter updated successfully",
                                        "cover_letter": {
                                            "id": updated_cover_letter.id,
                                            "name": updated_cover_letter.name,
                                            "email": updated_cover_letter.email,
                                            "phone_number": updated_cover_letter.phone_number,
                                            "company_name": updated_cover_letter.company_name,
                                            "job_title": updated_cover_letter.job_title,
                                            "cover_letter_content": updated_cover_letter.cover_letter_content,
                                            "generated_content": updated_cover_letter.generated_content,
                                            "parsed_content": updated_cover_letter.parsed_content,
                                        },
                                        "task_id": cover_letter_content_id,
                                    },
                                    status=status.HTTP_200_OK,
                                )
                            except CoverLetter.DoesNotExist:
                                logger.error(f"Cover letter with ID {cover_letter_id} not found for user {self.request.user.id}")
                                return Response(
                                    {
                                        "status": "Failed",
                                        "message": "Cover letter not found. Please ensure you have permission to update this cover letter.",
                                        "task_id": cover_letter_content_id,
                                    },
                                    status=status.HTTP_404_NOT_FOUND,
                                )
                        else:
                            logger.error(f"Failed to update cover letter with ID {cover_letter_id}")
                            return Response(
                                {
                                    "status": "Failed",
                                    "message": "Cover letter update completed but failed to save changes. Please try again.",
                                    "task_id": cover_letter_content_id,
                                },
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            )
                    except Exception as e:
                        logger.error(f"Failed to update cover letter: {e}")
                        return Response(
                            {
                                "status": "Failed",
                                "message": "Cover letter update completed but failed to update cover letter. Please try again.",
                                "task_id": cover_letter_content_id,
                            },
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        )

                # If task completed but no valid data
                logger.error(f"Update task {cover_letter_content_id} completed but no valid data found")
                return Response(
                    {
                        "status": "Failed",
                        "message": "Cover letter update completed but no valid data found. Please try again.",
                        "task_id": cover_letter_content_id,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Handle pending tasks
            cached_data = cover_letter_repo.get_task_result(cover_letter_content_result.id)

            if cached_data:
                # Task is complete but AsyncResult might not reflect it yet
                try:
                    cover_letter_id = cached_data.get("cover_letter_id")
                    if cover_letter_id:
                        update_success = cover_letter_repo.update_cover_letter(
                            cover_letter_id,
                            cached_data["original_content"],
                            cached_data["parsed_content"],
                            self.request.user,
                        )

                        if update_success:
                            updated_cover_letter = CoverLetter.objects.get(id=cover_letter_id, user=self.request.user)

                            # Clean up the cached data
                            cover_letter_repo.delete_task(cover_letter_content_id)
                            cover_letter_content_result.forget()

                            logger.info(f"Cover letter updated successfully with ID: {updated_cover_letter.id}")

                            return Response(
                                {
                                    "status": "Success",
                                    "message": "Cover letter updated successfully",
                                    "cover_letter": {
                                        "id": updated_cover_letter.id,
                                        "name": updated_cover_letter.name,
                                        "email": updated_cover_letter.email,
                                        "phone_number": updated_cover_letter.phone_number,
                                        "company_name": updated_cover_letter.company_name,
                                        "job_title": updated_cover_letter.job_title,
                                        "cover_letter_content": updated_cover_letter.cover_letter_content,
                                        "generated_content": updated_cover_letter.generated_content,
                                        "parsed_content": updated_cover_letter.parsed_content,
                                    },
                                    "task_id": cover_letter_content_id,
                                },
                                status=status.HTTP_200_OK,
                            )
                except Exception as e:
                    logger.error(f"Failed to update cover letter from cached data: {e}")
                    return Response(
                        {
                            "status": "Failed",
                            "message": "Cover letter update completed but failed to update cover letter. Please try again.",
                            "task_id": cover_letter_content_id,
                        },
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

            # Task is still pending
            logger.info(f"Update task {cover_letter_content_id} is still pending")
            return Response(
                {
                    "status": "Pending",
                    "message": "Cover letter update is still in progress. Please check again in a few moments.",
                    "task_id": cover_letter_content_id,
                    "task_state": cover_letter_content_result.state,
                },
                status=status.HTTP_202_ACCEPTED,
            )

        except BackendError:  # Raised when result backend can't find the task
            logger.error(
                f"Update task result for {cover_letter_content_id} has been deleted or doesn't exist."
            )
            return Response(
                {
                    "status": "Failed",
                    "message": "Task not found. Please generate content again.",
                    "task_id": cover_letter_content_id,
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except KeyError:  # Raised if task metadata is missing in Redis
            logger.error(f"Update task {cover_letter_content_id} not found in the backend.")
            try:
                cover_letter_content_result.forget()
            except:
                pass
            return Response(
                {
                    "status": "Failed",
                    "message": "Task metadata missing. Please generate content again.",
                    "task_id": cover_letter_content_id,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:  # Catch any unexpected errors
            logger.error(f"An unexpected error occurred during cover letter update: {e}")
            try:
                AsyncResult(cover_letter_content_id).revoke()
                AsyncResult(cover_letter_content_id).forget()
            except:
                pass

            return Response(
                {
                    "status": "Failed",
                    "message": "An unexpected error occurred. Please generate content again.",
                    "task_id": cover_letter_content_id,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# results view
# get a resume that belongs to user
class CoverLetterResultView(APIView):
    """Get a cover letter"""

    def get(self, request, cover_letter_task_id):
        """"""
        cover_letter_result = AsyncResult(cover_letter_task_id)

        if cover_letter_result.ready():
            result = cover_letter_result.result

            if isinstance(result, int):
                cover_letter = CoverLetter.objects.get(id="1")
                serializer = CoverLetterSerializer(cover_letter)

                return Response(
                    {
                        **serializer.data,
                        "parsed_content": json.loads(
                            serializer.data["parsed_content"].replace("'", '"')
                        ),
                    },
                    status=status.HTTP_200_OK,
                )
            return Response(
                {"error": "Cover letter not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            {"status": cover_letter_result.status},
            status=status.HTTP_202_ACCEPTED,
        )
