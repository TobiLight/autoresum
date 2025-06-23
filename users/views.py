import logging

from rest_framework import permissions, status
from rest_framework.generics import CreateAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenObtainPairView,
)

from users.models import User
from users.serializers import (
    UserSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
)
from rest_framework.permissions import AllowAny

logger = logging.getLogger(__name__)


class UserRegistrationView(CreateAPIView):
    """
    API view for user registration.

    This route handles the registration of a new user. It accepts user data,
    validates it, and creates a new user account. Upon successful registration,
    it returns the user's data along with access and refresh tokens.

    Attributes:
        serializer_class (UserSerializer): The serializer used to validate and
         create user data.

    Responses:
        - 201 Created: User registration successful, returns user data and
        tokens.
        - 400 Bad Request: User registration failed due to validation errors.

    Logging:
        Logs the registration process, including successful registrations
        and errors.
    """
    permission_classes = [AllowAny]
    serializer_class = UserSerializer

    def create(self, request):
        serializer = UserSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            headers = self.get_success_headers(serializer.data)

            logger.info(f"New user registered: {user.email}")
            return Response(
                {
                    **serializer.data,
                    "access_token": str(refresh.access_token),
                    "refresh_token": str(refresh),
                },
                status=status.HTTP_201_CREATED,
                headers=headers,
            )

        headers = self.get_success_headers(serializer.data)
        logger.error(f"Registration failed: {serializer.errors}")
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
            headers=headers,
        )


class UserLoginView(TokenObtainPairView):
    """
    API view for user login.

    This route handles user authentication. It accepts email and password,
    verifies the credentials, and returns access and refresh tokens upon success.

    Attributes:
        permission_classes (list): Allows any user to access this endpoint.

    Responses:
        - 200 OK: Login successful, returns tokens.
        - 400 Bad Request: Login failed due to missing or incorrect credentials.
        - 401 Unauthorized: Invalid credentials.

    Logging:
        Logs successful logins and authentication failures.
    """

    pass


class UserLogoutView(TokenBlacklistView):
    """
    API view for user logout.

    This view blacklists the refresh token, effectively logging the user out.

    Request:
        - POST request with `refresh` token.

    Responses:
        - 200 OK: Logout successful.
        - 401 Unauthorized: Invalid or missing token.
    """

    pass


class UserProfileView(RetrieveAPIView, UpdateAPIView):
    """
    API view for user profile management (retrieve and update).

    This endpoint allows authenticated users to view and update their complete profile information.
    Users can only access and modify their own profile data for security.

    URL:
        - GET /api/auth/profile - Retrieve profile
        - PATCH/PUT /api/auth/profile - Update profile

    Authentication: Required (IsAuthenticated)

    Updatable Fields: first_name, last_name, email

    Responses:
        - 200 OK: Profile retrieved/updated successfully
        - 400 Bad Request: Validation errors (update only)
        - 401 Unauthorized: User not authenticated

    Security: Users can only view/update their own profile data
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """Return the current authenticated user."""
        return self.request.user

    def get_serializer_class(self):
        """Return appropriate serializer based on request method."""
        if self.request.method in ['PATCH', 'PUT']:
            return UserProfileUpdateSerializer
        return UserProfileSerializer

    def retrieve(self, request, *args, **kwargs):
        """Retrieve user profile with custom response format."""
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        logger.info(f"User profile retrieved for user: {instance.username}")

        return Response(
            {
                "status": "Success",
                "message": "Profile retrieved successfully",
                "user": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def update(self, request, *args, **kwargs):
        """Update user profile with custom response format."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        if serializer.is_valid():
            self.perform_update(serializer)

            # Get updated user data using profile serializer
            profile_serializer = UserProfileSerializer(instance)

            logger.info(f"User profile updated for user: {instance.username}")

            return Response(
                {
                    "status": "Success",
                    "message": "Profile updated successfully",
                    "user": profile_serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        else:
            logger.error(f"Profile update failed for user {instance.username}: {serializer.errors}")
            return Response(
                {
                    "status": "Failed",
                    "message": "Profile update failed",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    def partial_update(self, request, *args, **kwargs):
        """Handle PATCH requests."""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
