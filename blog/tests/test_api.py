import io
import os

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from blog.models import Blog, Category


class BlogAPITests(APITestCase):
    """
    Comprehensive unit tests for the Blog REST APIs, verifying list, detail,
    create, update, and delete actions alongside the RBAC permission mappings.
    """

    def setUp(self):
        # Generate a valid 1x1 pixel PNG in memory to bypass Pillow validation
        img_buffer = io.BytesIO()
        img = Image.new("RGBA", size=(1, 1), color=(255, 0, 0))
        img.save(img_buffer, "png")
        self.test_image_data = img_buffer.getvalue()

        # Retrieve predefined database permission groups
        self.author_group = Group.objects.get(name="Author")
        self.editor_group = Group.objects.get(name="Editor")
        self.publisher_group = Group.objects.get(name="Publisher")

        # Create test users matching the application groups
        self.author_user = User.objects.create_user(
            username="author@example.com",
            email="author@example.com",
            password="Password123",
        )
        self.author_user.groups.add(self.author_group)

        self.editor_user = User.objects.create_user(
            username="editor@example.com",
            email="editor@example.com",
            password="Password123",
        )
        self.editor_user.groups.add(self.editor_group)

        self.publisher_user = User.objects.create_user(
            username="publisher@example.com",
            email="publisher@example.com",
            password="Password123",
        )
        self.publisher_user.groups.add(self.publisher_group)

        # Standard user without special group permissions
        self.regular_user = User.objects.create_user(
            username="regular@example.com",
            email="regular@example.com",
            password="Password123",
        )

        # Setup an initial blog post instance
        self.blog = Blog.objects.create(
            title="Initial API Blog Title",
            content="Initial content description body.",
            category=Category.PYTHON,
            tags="python, tutorial",
            author=self.author_user,
            editor=self.editor_user,
            publisher=self.publisher_user,
        )

        # API Endpoints
        self.list_create_url = reverse("blog_api:blog-list")
        self.detail_url = reverse("blog_api:blog-detail", kwargs={"pk": self.blog.pk})

    def test_anonymous_access_denied(self):
        """
        Verify that unauthenticated users are rejected with a 403 Forbidden response.
        """
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_regular_user_access_denied(self):
        """
        Verify that authenticated users without blog permissions are rejected.
        """
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_author_permissions(self):
        """
        Verify that Authors can retrieve and create posts but cannot update or delete.
        """
        self.client.force_authenticate(user=self.author_user)

        # Can GET list
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Can GET detail
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Initial API Blog Title")
        self.assertIn("python", response.data["tags_list"])

        # Can POST create
        data = {
            "title": "Author Created Blog",
            "content": "Valid blog content body.",
            "category": Category.DJANGO,
            "tags": "django, views",
            "author": self.author_user.id,
        }
        response = self.client.post(self.list_create_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Cannot PUT update
        update_data = {
            "title": "Title Modified By Author",
            "content": "Updated content body.",
            "category": Category.PYTHON,
        }
        response = self.client.put(self.detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Cannot DELETE
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_editor_permissions(self):
        """
        Verify that Editors can retrieve, create, and update posts but cannot delete.
        """
        self.client.force_authenticate(user=self.editor_user)

        # Can PUT update
        update_data = {
            "title": "Title Modified By Editor",
            "content": "Updated content body by editor.",
            "category": Category.SCRAPY,
            "tags": "scrapy, webscraping",
        }
        response = self.client.put(self.detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.blog.refresh_from_db()
        self.assertEqual(self.blog.title, "Title Modified By Editor")

        # Cannot DELETE
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_publisher_permissions(self):
        """
        Verify that Publishers have full CRUD rights, including deletion.
        """
        self.client.force_authenticate(user=self.publisher_user)

        # Can DELETE
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Blog.objects.filter(pk=self.blog.pk).exists())

    def test_validation_errors(self):
        """
        Verify that validation constraints match database and model restrictions.
        """
        self.client.force_authenticate(user=self.publisher_user)

        # 1. Whitespace title validation check
        data = {
            "title": "     ",
            "content": "Valid content descriptions.",
            "category": Category.PYTHON,
        }
        response = self.client.post(self.list_create_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title", response.data)

        # 2. Invalid category choices check
        data = {
            "title": "Valid Blog Title",
            "content": "Valid content descriptions.",
            "category": "RustLanguage",
        }
        response = self.client.post(self.list_create_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("category", response.data)

    def test_group_user_assignment_validation(self):
        """
        Verify that serializer limits ForeignKey selection to members of correct Groups.
        """
        self.client.force_authenticate(user=self.publisher_user)

        # Assign editor_user to the author field (invalid group check)
        data = {
            "title": "Invalid Author Assignment",
            "content": "Content desc.",
            "category": Category.PYTHON,
            "author": self.editor_user.id,
        }
        response = self.client.post(self.list_create_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("author", response.data)

    def test_image_cleanup_on_destroy_and_update(self):
        """
        Verify that cover photos are cleanly purged from disk on instance update and destroy.
        """
        self.client.force_authenticate(user=self.publisher_user)

        # Attach test cover image
        test_file = SimpleUploadedFile(
            "api_cover.png", self.test_image_data, content_type="image/png"
        )

        self.blog.image = test_file
        self.blog.save()

        image_path = self.blog.image.path
        self.assertTrue(os.path.exists(image_path))

        # 1. Test replacement updates cleanup
        replacement_file = SimpleUploadedFile(
            "api_replacement.png", self.test_image_data, content_type="image/png"
        )
        data = {
            "title": self.blog.title,
            "content": self.blog.content,
            "category": self.blog.category,
            "image": replacement_file,
        }
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.put(self.detail_url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify the old file was removed
        self.assertFalse(os.path.exists(image_path))

        # Get path of new image
        self.blog.refresh_from_db()
        new_image_path = self.blog.image.path
        self.assertTrue(os.path.exists(new_image_path))

        # 2. Test deletion cleanup
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(os.path.exists(new_image_path))
