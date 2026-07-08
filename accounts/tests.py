import re
from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from accounts.forms import EmailAuthenticationForm, SignupForm


class AuthenticationTests(TestCase):
    """
    Unit tests covering signup form validations (password mismatch, email uniqueness,
    password complexity), and email-based login/logout sessions.
    """

    def setUp(self):
        # Create a default test user
        self.user = User.objects.create_user(
            username="testuser@example.com",
            email="testuser@example.com",
            password="Password123",
            first_name="Test",
            last_name="User",
        )

        # Ensure groups exist
        self.author_group, _ = Group.objects.get_or_create(name="Author")
        self.user.groups.add(self.author_group)

    # ==========================================
    # 1. SIGNUP FORM VALIDATION TESTS
    # ==========================================
    def test_signup_validation_passwords_mismatch(self):
        """Ensure signup fails when password and confirm_password do not match."""
        data = {
            "full_name": "New User",
            "email": "new@example.com",
            "group": "Author",
            "password": "Password123",
            "confirm_password": "DifferentPassword123",
        }
        form = SignupForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("confirm_password", form.errors)

    def test_signup_validation_email_uniqueness(self):
        """Ensure signup fails when email address already exists (case-insensitive)."""
        data = {
            "full_name": "Dup User",
            "email": "TESTUSER@example.com",  # Uppercase to test case-insensitive check
            "group": "Author",
            "password": "Password123",
            "confirm_password": "Password123",
        }
        form = SignupForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_signup_validation_password_strength(self):
        """Ensure signup validation fails on insecure/weak passwords."""
        # Test short password
        form = SignupForm(
            data={
                "full_name": "User",
                "email": "ok@example.com",
                "group": "Author",
                "password": "short",
                "confirm_password": "short",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("password", form.errors)

        # Test password missing digits
        form = SignupForm(
            data={
                "full_name": "User",
                "email": "ok@example.com",
                "group": "Author",
                "password": "NoDigitsPassword",
                "confirm_password": "NoDigitsPassword",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("password", form.errors)

    # ==========================================
    # 2. LOGIN & AUTHENTICATION TESTS
    # ==========================================
    def test_email_login_success(self):
        """Verify login succeeds using the custom backend with email and password."""
        login_data = {
            "username": "testuser@example.com",
            "password": "Password123",
        }
        response = self.client.post(reverse("accounts:login"), login_data)
        self.assertRedirects(response, reverse("blog:list"))

    def test_email_login_case_insensitive(self):
        """Verify login is case-insensitive for the email address."""
        login_data = {
            "username": "TESTUSER@EXAMPLE.COM",
            "password": "Password123",
        }
        response = self.client.post(reverse("accounts:login"), login_data)
        self.assertRedirects(response, reverse("blog:list"))

    def test_email_login_failure(self):
        """Verify login fails on wrong credentials and renders error."""
        login_data = {
            "username": "testuser@example.com",
            "password": "WrongPassword",
        }
        response = self.client.post(reverse("accounts:login"), login_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter a correct email address")

    def test_logout_redirect(self):
        """Verify logout destroys session and redirects to login."""
        self.client.login(username="testuser@example.com", password="Password123")
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("accounts:login"))

    # ==========================================
    # 3. PASSWORD RESET TESTS
    # ==========================================
    def test_password_reset_post_sends_email(self):
        """Ensure password reset triggers email dispatch to console/outbox."""
        from django.core import mail
        response = self.client.post(
            reverse("accounts:password_reset"),
            {"email": "testuser@example.com"}
        )
        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "TechBlogs Password Reset Request")
        self.assertIn("testuser@example.com", mail.outbox[0].to)

    def test_password_reset_confirm_invalid_link(self):
        """Ensure invalid tokens display appropriate link expiration feedback."""
        invalid_url = reverse(
            "accounts:password_reset_confirm",
            kwargs={"uidb64": "invaliduid", "token": "invalidtoken"}
        )
        response = self.client.get(invalid_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid Token / Link Expired")
