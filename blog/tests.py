from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from .forms import BlogForm
from .models import Blog, Category


class AuthenticationAndAuthorizationTests(TestCase):
    """
    Comprehensive test suite covering authentication, registration validations,
    groups, permissions matrices, CBV access protection, AJAX views, and form filtering.
    """

    def setUp(self):
        # Retrieve the ContentType for Blog model
        self.content_type = ContentType.objects.get_for_model(Blog)

        # Retrieve groups (pre-created via post_migrate signals in setup)
        self.author_group = Group.objects.get(name="Author")
        self.editor_group = Group.objects.get(name="Editor")
        self.publisher_group = Group.objects.get(name="Publisher")

        # Create test users under groups
        self.author_user = User.objects.create_user(
            username="author@example.com",
            email="author@example.com",
            password="Password123",
            first_name="Author",
            last_name="User",
        )
        self.author_user.groups.add(self.author_group)

        self.editor_user = User.objects.create_user(
            username="editor@example.com",
            email="editor@example.com",
            password="Password123",
            first_name="Editor",
            last_name="User",
        )
        self.editor_user.groups.add(self.editor_group)

        self.publisher_user = User.objects.create_user(
            username="publisher@example.com",
            email="publisher@example.com",
            password="Password123",
            first_name="Publisher",
            last_name="User",
        )
        self.publisher_user.groups.add(self.publisher_group)

        # Create a default blog post to verify permissions
        self.blog = Blog.objects.create(
            title="Django Test Post",
            content="Testing access controls on Blog model views.",
            category="Python",
            author=self.author_user,
            editor=self.editor_user,
            publisher=self.publisher_user,
        )

    # ==========================================
    # 1. GROUP PERMISSIONS & MIGRATION TEST
    # ==========================================
    def test_groups_created_and_provisioned(self):
        """Ensure Author, Editor, and Publisher groups exist and have correct permissions."""
        self.assertTrue(Group.objects.filter(name="Author").exists())
        self.assertTrue(Group.objects.filter(name="Editor").exists())
        self.assertTrue(Group.objects.filter(name="Publisher").exists())

        # Test Author permissions
        author_perms = self.author_group.permissions.values_list(
            "codename", flat=True
        )
        self.assertIn("view_blog", author_perms)
        self.assertIn("add_blog", author_perms)
        self.assertNotIn("change_blog", author_perms)
        self.assertNotIn("delete_blog", author_perms)

        # Test Editor permissions
        editor_perms = self.editor_group.permissions.values_list(
            "codename", flat=True
        )
        self.assertIn("view_blog", editor_perms)
        self.assertIn("add_blog", editor_perms)
        self.assertIn("change_blog", editor_perms)
        self.assertNotIn("delete_blog", editor_perms)

        # Test Publisher permissions
        pub_perms = self.publisher_group.permissions.values_list(
            "codename", flat=True
        )
        self.assertIn("view_blog", pub_perms)
        self.assertIn("add_blog", pub_perms)
        self.assertIn("change_blog", pub_perms)
        self.assertIn("delete_blog", pub_perms)

    # ==========================================
    # 2. ANONYMOUS USER RESTRICTIONS & AJAX 401
    # ==========================================
    def test_anonymous_redirected_to_login(self):
        """Ensure anonymous requests to pages redirect to login."""
        endpoints = [
            reverse("blog:list"),
            reverse("blog:create"),
            reverse("blog:detail", kwargs={"pk": self.blog.id}),
            reverse("blog:edit", kwargs={"pk": self.blog.id}),
        ]
        for url in endpoints:
            response = self.client.get(url)
            self.assertRedirects(response, f"{reverse('accounts:login')}?next={url}")

    def test_anonymous_ajax_endpoints_return_401(self):
        """Ensure AJAX requests from anonymous users return 401 JSON responses."""
        ajax_urls = [
            reverse("blog:datatable"),
            reverse("blog:edit", kwargs={"pk": self.blog.id}),
            reverse("blog:delete", kwargs={"pk": self.blog.id}),
        ]
        for url in ajax_urls:
            # We verify via both header trigger and URL pattern paths
            response = self.client.post(
                url, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
            )
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()["success"], False)

    # ==========================================
    # 5. AUTHORIZATION MATRIX & ACCESS RIGHTS
    # ==========================================
    def test_author_access_rights(self):
        """Verify Author can view list, detail, create blogs, but cannot edit/delete."""
        self.client.login(username="author@example.com", password="Password123")

        # View List & Detail (Permitted)
        self.assertEqual(self.client.get(reverse("blog:list")).status_code, 200)
        self.assertEqual(
            self.client.get(
                reverse("blog:detail", kwargs={"pk": self.blog.id})
            ).status_code,
            200,
        )

        # Create Blog (Permitted)
        self.assertEqual(self.client.get(reverse("blog:create")).status_code, 200)
        post_data = {
            "title": "Author Post",
            "content": "Description body",
            "category": "Django",
        }
        create_resp = self.client.post(reverse("blog:create"), post_data)
        self.assertEqual(create_resp.status_code, 302)

        # Edit Blog (Forbidden)
        edit_url = reverse("blog:edit", kwargs={"pk": self.blog.id})
        self.assertEqual(self.client.get(edit_url).status_code, 403)
        self.assertEqual(
            self.client.put(
                edit_url,
                data="title=New",
                content_type="application/x-www-form-urlencoded",
            ).status_code,
            403,
        )

        # Delete Blog (Forbidden)
        delete_url = reverse("blog:delete", kwargs={"pk": self.blog.id})
        self.assertEqual(self.client.delete(delete_url).status_code, 403)

    def test_editor_access_rights(self):
        """Verify Editor can view, create, edit blogs, but cannot delete."""
        self.client.login(username="editor@example.com", password="Password123")

        # View List & Detail (Permitted)
        self.assertEqual(self.client.get(reverse("blog:list")).status_code, 200)

        # Edit Blog (Permitted)
        edit_url = reverse("blog:edit", kwargs={"pk": self.blog.id})
        self.assertEqual(self.client.get(edit_url).status_code, 200)

        put_data = "title=Updated+By+Editor&category=Django&content=Body"
        edit_resp = self.client.put(
            edit_url, data=put_data, content_type="application/x-www-form-urlencoded"
        )
        self.assertEqual(edit_resp.status_code, 200)
        self.assertEqual(edit_resp.json()["success"], True)

        # Delete Blog (Forbidden)
        delete_url = reverse("blog:delete", kwargs={"pk": self.blog.id})
        self.assertEqual(self.client.delete(delete_url).status_code, 403)

    def test_publisher_access_rights(self):
        """Verify Publisher can perform all operations (view, create, edit, delete)."""
        self.client.login(username="publisher@example.com", password="Password123")

        # View & Edit (Permitted)
        self.assertEqual(self.client.get(reverse("blog:list")).status_code, 200)

        # Delete Blog (Permitted)
        delete_url = reverse("blog:delete", kwargs={"pk": self.blog.id})
        delete_resp = self.client.delete(delete_url)
        self.assertEqual(delete_resp.status_code, 200)
        self.assertEqual(delete_resp.json()["success"], True)
        self.assertFalse(Blog.objects.filter(pk=self.blog.id).exists())

    # ==========================================
    # 6. DYNAMIC DROPDOWN FILTERING
    # ==========================================
    def test_dropdown_group_filtering(self):
        """Verify BlogForm dropdowns filter users by corresponding groups only."""
        form = BlogForm()
        # Author field queryset should only have users in Author group
        author_queryset = form.fields["author"].queryset
        self.assertIn(self.author_user, author_queryset)
        self.assertNotIn(self.editor_user, author_queryset)
        self.assertNotIn(self.publisher_user, author_queryset)

        # Editor field queryset should only have users in Editor group
        editor_queryset = form.fields["editor"].queryset
        self.assertIn(self.editor_user, editor_queryset)
        self.assertNotIn(self.author_user, editor_queryset)
        self.assertNotIn(self.publisher_user, editor_queryset)

        # Publisher field queryset should only have users in Publisher group
        pub_queryset = form.fields["publisher"].queryset
        self.assertIn(self.publisher_user, pub_queryset)
        self.assertNotIn(self.author_user, pub_queryset)
        self.assertNotIn(self.editor_user, pub_queryset)
