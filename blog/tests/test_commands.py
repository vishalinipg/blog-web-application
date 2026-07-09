from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from blog.models import Blog, Category


class AssignBlogRoleCommandTestCase(TestCase):
    def setUp(self):
        # Retrieve Roles/Groups
        self.author_group = Group.objects.get(name="Author")
        self.editor_group = Group.objects.get(name="Editor")
        self.publisher_group = Group.objects.get(name="Publisher")

        # Create Users
        self.author_user = User.objects.create_user(
            username="author@example.com",
            email="author@example.com",
            password="Password123",
            first_name="Alice",
            last_name="Author",
        )
        self.author_user.groups.add(self.author_group)

        self.editor_user = User.objects.create_user(
            username="editor@example.com",
            email="editor@example.com",
            password="Password123",
            first_name="Ed",
            last_name="Editor",
        )
        self.editor_user.groups.add(self.editor_group)

        self.publisher_user = User.objects.create_user(
            username="publisher@example.com",
            email="publisher@example.com",
            password="Password123",
            first_name="Pub",
            last_name="Publisher",
        )
        self.publisher_user.groups.add(self.publisher_group)

        # Create Blog
        self.blog = Blog.objects.create(
            title="Notification Setup",
            content="Blog text",
            category=Category.DJANGO,
        )

    @patch(
        "blog.management.commands.assign_blog_role.send_role_assignment_notification_task.delay"
    )
    def test_assign_author_success(self, mock_notify):
        call_command(
            "assign_blog_role",
            "--blog-id",
            self.blog.id,
            "--group",
            "Author",
            "--email",
            "author@example.com",
        )

        # Verify DB Persistence
        self.blog.refresh_from_db()
        self.assertEqual(self.blog.author, self.author_user)

        # Verify Async Notification was triggered (1 call: assignment)
        mock_notify.assert_called_once_with(
            self.author_user.id, self.blog.id, "Author", is_unassignment=False
        )

    @patch(
        "blog.management.commands.assign_blog_role.send_role_assignment_notification_task.delay"
    )
    def test_reassign_author_success_with_unassignment(self, mock_notify):
        # Set initial author
        self.blog.author = self.author_user
        self.blog.save()

        # Create another author user
        new_author = User.objects.create_user(
            username="newauthor@example.com",
            email="newauthor@example.com",
            password="Password123",
        )
        new_author.groups.add(self.author_group)

        call_command(
            "assign_blog_role",
            "--blog-id",
            self.blog.id,
            "--group",
            "Author",
            "--email",
            "newauthor@example.com",
        )

        # Verify DB Persistence
        self.blog.refresh_from_db()
        self.assertEqual(self.blog.author, new_author)

        # Verify both unassignment and assignment notifications triggered
        self.assertEqual(mock_notify.call_count, 2)
        # First call is unassignment for old user
        mock_notify.assert_any_call(
            self.author_user.id, self.blog.id, "Author", is_unassignment=True
        )
        # Second call is assignment for new user
        mock_notify.assert_any_call(
            new_author.id, self.blog.id, "Author", is_unassignment=False
        )

    def test_invalid_blog_id(self):
        with self.assertRaises(CommandError) as context:
            call_command(
                "assign_blog_role",
                "--blog-id",
                9999,
                "--group",
                "Author",
                "--email",
                "author@example.com",
            )
        self.assertIn("Blog post with ID 9999 does not exist", str(context.exception))

    def test_invalid_email(self):
        with self.assertRaises(CommandError) as context:
            call_command(
                "assign_blog_role",
                "--blog-id",
                self.blog.id,
                "--group",
                "Author",
                "--email",
                "nonexistent@example.com",
            )
        self.assertIn(
            "User with email 'nonexistent@example.com' does not exist",
            str(context.exception),
        )

    def test_user_not_in_group(self):
        # Alice is in Author group, but we try to assign her as Editor
        with self.assertRaises(CommandError) as context:
            call_command(
                "assign_blog_role",
                "--blog-id",
                self.blog.id,
                "--group",
                "Editor",
                "--email",
                "author@example.com",
            )
        self.assertIn(
            "does not belong to the 'Editor' group",
            str(context.exception),
        )

    def test_duplicate_role_assignment(self):
        # Set author user
        self.blog.author = self.author_user
        self.blog.save()

        # Try to assign the same author user again
        with self.assertRaises(CommandError) as context:
            call_command(
                "assign_blog_role",
                "--blog-id",
                self.blog.id,
                "--group",
                "Author",
                "--email",
                "author@example.com",
            )
        self.assertIn(
            "is already assigned as Author on this blog", str(context.exception)
        )

    def test_multiple_users_exist_with_email(self):
        # Create a second user with the same email address
        duplicate_user = User.objects.create_user(
            username="duplicate_author",
            email="author@example.com",
            password="Password123",
        )
        duplicate_user.groups.add(self.author_group)

        with self.assertRaises(CommandError) as context:
            call_command(
                "assign_blog_role",
                "--blog-id",
                self.blog.id,
                "--group",
                "Author",
                "--email",
                "author@example.com",
            )
        self.assertIn(
            "Multiple users exist with email 'author@example.com'",
            str(context.exception),
        )
