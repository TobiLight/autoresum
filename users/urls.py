from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from users.views import (
    UserLoginView,
    UserLogoutView,
    UserRegistrationView,
    UserProfileView,
)

urlpatterns = [
    # Authentication endpoints
    path("register", UserRegistrationView.as_view(), name="register"),
    path("login", UserLoginView.as_view(), name="login"),
    path("logout", UserLogoutView.as_view(), name="logout"),
    path("token/refresh", TokenRefreshView.as_view(), name="token_refresh"),

    # User profile management endpoints
    path("profile", UserProfileView.as_view(), name="user_profile"),
]
