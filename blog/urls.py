from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from .forms import EmailAuthenticationForm
from .views import (
    BlogAjaxDatatableView,
    BlogCreateView,
    BlogDeleteView,
    BlogDetailView,
    BlogListView,
    BlogUpdateView,
    SignupView,
)

app_name = "blog"

urlpatterns = [
    # Authentication routes
    path(
        "login/",
        LoginView.as_view(
            template_name="blog/login.html",
            authentication_form=EmailAuthenticationForm,
        ),
        name="login",
    ),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("signup/", SignupView.as_view(), name="signup"),
    # Core Blog app routes
    path("", BlogListView.as_view(), name="list"),
    path("blogs/datatable/", BlogAjaxDatatableView.as_view(), name="datatable"),
    path("blogs/create/", BlogCreateView.as_view(), name="create"),
    path("blogs/<int:pk>/edit/", BlogUpdateView.as_view(), name="edit"),
    path("blogs/<int:pk>/", BlogDetailView.as_view(), name="detail"),
    path("blogs/<int:pk>/delete/", BlogDeleteView.as_view(), name="delete"),
]
