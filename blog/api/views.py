from rest_framework.generics import (ListCreateAPIView,
                                     RetrieveUpdateDestroyAPIView)
from rest_framework.permissions import DjangoModelPermissions

from blog.models import Blog
from blog.utils import delete_file_on_commit

from .serializers import BlogSerializer


class BlogModelPermissions(DjangoModelPermissions):
    """
    Subclass of DjangoModelPermissions to map safe read-only requests (GET)
    to Django's built-in 'view_blog' database permission constraint.
    """

    def __init__(self):
        super().__init__()
        self.perms_map = dict(self.perms_map)  # Copy to avoid mutating parent class
        self.perms_map["GET"] = ["%(app_label)s.view_%(model_name)s"]
        self.perms_map["OPTIONS"] = ["%(app_label)s.view_%(model_name)s"]
        self.perms_map["HEAD"] = ["%(app_label)s.view_%(model_name)s"]


class BlogListCreateAPIView(ListCreateAPIView):
    """
    API endpoint for listing existing blog entries (GET) and creating new blog posts (POST).
    Inherits auth/permission rules globally.
    """

    queryset = Blog.objects.all()
    serializer_class = BlogSerializer
    permission_classes = [BlogModelPermissions]


class BlogRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    """
    API endpoint for retrieving (GET), updating (PUT/PATCH), and deleting (DELETE) blog posts.
    """

    queryset = Blog.objects.all()
    serializer_class = BlogSerializer
    permission_classes = [BlogModelPermissions]

    def perform_destroy(self, instance):
        """
        Delete associated media file from storage on database record deletion.
        """
        old_image = instance.image if instance.image else None
        instance.delete()
        if old_image:
            delete_file_on_commit(old_image)

    def perform_update(self, serializer):
        """
        Override updates to clean up obsolete media files on substitution.
        """
        instance = self.get_object()
        old_image = instance.image if instance.image else None

        updated_instance = serializer.save()

        # Delete the previous cover photo if replaced with a new upload
        new_image = serializer.validated_data.get("image")
        if new_image and old_image:
            delete_file_on_commit(old_image)
