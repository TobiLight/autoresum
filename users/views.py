import logging

from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenObtainPairView,
)

from users.serializers import UserSerializer

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
