from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from users.views import UserLoginView, UserLogoutView, UserRegistrationView

urlpatterns = [
    path("register", UserRegistrationView.as_view(), name="register"),
    path("login", UserLoginView.as_view(), name="login"),
    path("logout", UserLogoutView.as_view(), name="logout"),
    path("token/refresh", TokenRefreshView.as_view(), name="token_refresh"),
]
