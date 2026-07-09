from django.contrib.auth import views as auth_views
from django.urls import path

from .views import (CeleryPasswordResetView, EmailLoginView,
                    PasswordResetCompleteView, PasswordResetConfirmView,
                    PasswordResetDoneView, SignupView)

app_name = "accounts"

urlpatterns = [
    path("login/", EmailLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("signup/", SignupView.as_view(), name="signup"),
    # Password Reset Views
    path("password-reset/", CeleryPasswordResetView.as_view(), name="password_reset"),
    path(
        "password-reset/done/",
        PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "password-reset-confirm/<uidb64>/<token>/",
        PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/complete/",
        PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
]
