from django.urls import path

from .views import BlogListCreateAPIView, BlogRetrieveUpdateDestroyAPIView

app_name = "blog_api"

urlpatterns = [
    path("blogs/", BlogListCreateAPIView.as_view(), name="blog-list"),
    path("blogs/<int:pk>/", BlogRetrieveUpdateDestroyAPIView.as_view(), name="blog-detail"),
]
