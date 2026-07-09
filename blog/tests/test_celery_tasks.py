import datetime
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.core import mail
from django.test import TestCase
from django.utils import timezone

from blog.models import Blog, Category
from worker.tasks import (send_password_reset_email_async,
                          send_role_assignment_notification_task,
                          send_weekly_author_submissions_email_task,
                          send_weekly_author_submissions_report)


class CeleryTasksTestCase(TestCase):
    def setUp(self):
        # Set up Groups
        self.author_group = Group.objects.get(name="Author")
        self.editor_group = Group.objects.get(name="Editor")
        self.publisher_group = Group.objects.get(name="Publisher")

        # Set up Users
        self.author_user = User.objects.create_user(
            username="author@example.com",
            email="author@example.com",
            password="Password123",
            first_name="Alice",
            last_name="Author",
        )
        self.author_user.groups.add(self.author_group)

        self.publisher_user = User.objects.create_user(
            username="publisher@example.com",
            email="publisher@example.com",
            password="Password123",
            first_name="Bob",
            last_name="Publisher",
        )
        self.publisher_user.groups.add(self.publisher_group)

    def test_weekly_author_submissions_email_with_blogs(self):
        # Create a blog post dated in the previous week
        today = timezone.localtime(timezone.now()).date()
        start_of_prev_week = today - datetime.timedelta(days=today.weekday() + 7)
        prev_week_time = timezone.make_aware(
            datetime.datetime.combine(start_of_prev_week, datetime.time(12, 0))
        )

        blog = Blog.objects.create(
            title="Weekly Post",
            content="Some weekly content",
            category=Category.PYTHON,
            author=self.author_user,
            publisher=self.publisher_user,
            publish=True,
        )
        # Update created_at using queryset update to bypass auto_now_add restrictions
        Blog.objects.filter(pk=blog.pk).update(created_at=prev_week_time)

        # Trigger task directly
        start_str = (prev_week_time - datetime.timedelta(hours=12)).isoformat()
        end_str = (prev_week_time + datetime.timedelta(days=1)).isoformat()

        send_weekly_author_submissions_email_task(
            self.author_user.id, start_str, end_str
        )

        # Verify email was sent and contains details
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, [self.author_user.email])
        self.assertEqual(email.subject, "Weekly Blog Submission Report")
        self.assertIn("Weekly Post", email.body)
        self.assertIn("Python", email.body)
        self.assertIn("Bob Publisher", email.body)

    def test_weekly_author_submissions_email_with_no_blogs(self):
        # Trigger task directly with no blogs in range
        today = timezone.localtime(timezone.now()).date()
        start_str = (today - datetime.timedelta(days=7)).isoformat()
        end_str = today.isoformat()

        send_weekly_author_submissions_email_task(
            self.author_user.id, start_str, end_str
        )

        # Verify email was sent and reports 0 blogs
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, [self.author_user.email])
        self.assertIn("Total blogs uploaded this week: 0", email.body)
        self.assertIn(
            "No blog submissions were recorded during this period.", email.body
        )

    def test_weekly_author_submissions_email_with_no_publisher(self):
        # Create a blog post with no publisher
        today = timezone.localtime(timezone.now()).date()
        start_of_prev_week = today - datetime.timedelta(days=today.weekday() + 7)
        prev_week_time = timezone.make_aware(
            datetime.datetime.combine(start_of_prev_week, datetime.time(12, 0))
        )

        blog = Blog.objects.create(
            title="Unpublished Post",
            content="Unpublished weekly content",
            category=Category.DJANGO,
            author=self.author_user,
            publisher=None,
            publish=True,
        )
        Blog.objects.filter(pk=blog.pk).update(created_at=prev_week_time)

        start_str = (prev_week_time - datetime.timedelta(hours=12)).isoformat()
        end_str = (prev_week_time + datetime.timedelta(days=1)).isoformat()

        send_weekly_author_submissions_email_task(
            self.author_user.id, start_str, end_str
        )

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn("Not Assigned", email.body)

    @patch("worker.tasks.send_weekly_author_submissions_email_task.delay")
    def test_send_weekly_author_submissions_report_triggers_delay(self, mock_delay):
        send_weekly_author_submissions_report()
        # Verify delay was called for our author
        mock_delay.assert_called_once()

    def test_send_role_assignment_notification_assignment(self):
        blog = Blog.objects.create(
            title="Test Blog Notifications",
            content="Notification test body",
            category=Category.PYTHON,
        )

        send_role_assignment_notification_task(
            self.author_user.id, blog.id, "Author", is_unassignment=False
        )

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, [self.author_user.email])
        self.assertIn(
            "Assigned as Author for blog: Test Blog Notifications", email.subject
        )
        self.assertIn("assigned as Author", email.body)

    def test_send_role_assignment_notification_unassignment(self):
        blog = Blog.objects.create(
            title="Test Blog Notifications Removal",
            content="Notification test body",
            category=Category.PYTHON,
        )

        send_role_assignment_notification_task(
            self.author_user.id, blog.id, "Author", is_unassignment=True
        )

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, [self.author_user.email])
        self.assertIn(
            "Removed as Author from blog: Test Blog Notifications Removal",
            email.subject,
        )
        self.assertIn("removed as Author", email.body)

    def test_send_password_reset_email_async(self):
        # Create user context similar to what Django's password reset creates
        context_dict = {
            "email": self.author_user.email,
            "domain": "testserver",
            "site_name": "TechBlogs",
            "uid": "MTI",
            "user_id": self.author_user.id,
            "token": "some-valid-token-mock",
            "protocol": "http",
        }

        send_password_reset_email_async(
            subject_template_name="emails/password_reset_subject.txt",
            email_template_name="emails/password_reset.txt",
            context_dict=context_dict,
            from_email="webmaster@localhost",
            to_email=self.author_user.email,
            html_email_template_name="emails/password_reset.html",
        )

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, [self.author_user.email])
        self.assertEqual(email.subject, "TechBlogs Password Reset Request")
        self.assertIn(
            "http://testserver/password-reset-confirm/MTI/some-valid-token-mock/",
            email.body,
        )
