import re
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User

from .models import Blog


class SignupForm(forms.Form):
    """
    Form for registering new users. Enforces validation rules for emails,
    matching passwords, selected groups, and password complexity.
    """

    full_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={"class": "form-control form-control-user", "placeholder": "Full Name"}
        ),
        label="Full Name",
    )
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": "form-control form-control-user",
                "placeholder": "Email Address",
            }
        ),
        label="Email Address",
    )
    group = forms.ChoiceField(
        choices=[
            ("", "Select Group"),
            ("Author", "Author"),
            ("Editor", "Editor"),
            ("Publisher", "Publisher"),
        ],
        widget=forms.Select(attrs={"class": "form-control"}),
        label="User Group",
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control form-control-user", "placeholder": "Password"}
        ),
        label="Password",
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control form-control-user",
                "placeholder": "Repeat Password",
            }
        ),
        label="Confirm Password",
    )

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        if not email:
            raise forms.ValidationError("This field is required.")
        # Check uniqueness against email and username fields in case-insensitive check
        if (
            User.objects.filter(email__iexact=email).exists()
            or User.objects.filter(username__iexact=email).exists()
        ):
            raise forms.ValidationError(
                "A user with this email address already exists."
            )
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        # Passwords match validation
        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match.")

        # Password strength validation
        if password:
            if len(password) < 8:
                self.add_error(
                    "password", "Password must be at least 8 characters long."
                )
            if not re.search(r"[A-Za-z]", password):
                self.add_error(
                    "password", "Password must contain at least one letter."
                )
            if not re.search(r"\d", password):
                self.add_error(
                    "password", "Password must contain at least one number."
                )

        return cleaned_data


class EmailAuthenticationForm(AuthenticationForm):
    """
    Subclasses Django's standard AuthenticationForm to swap the username input field
    with an email field styled for the SB Admin 2 login screen.
    """

    error_messages = {
        "invalid_login": (
            "Please enter a correct email address and password. Note that both "
            "fields may be case-sensitive."
        ),
        "inactive": "This account is inactive.",
    }

    username = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control form-control-user",
                "placeholder": "Enter Email Address...",
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control form-control-user",
                "placeholder": "Password",
            }
        ),
    )


class BlogForm(forms.ModelForm):
    """
    ModelForm for Blog model instance validation and representation.
    Applies standard Bootstrap 4 form field classes (form-control, form-control-file)
    to match the SB Admin 2 styling constraints.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # On update (instance exists and has pk), the image is not required to be re-uploaded
        if self.instance and self.instance.pk:
            self.fields["image"].required = False

        # Dynamically filter ForeignKey querysets to users belonging to corresponding groups
        self.fields["author"].queryset = User.objects.filter(groups__name="Author")
        self.fields["editor"].queryset = User.objects.filter(groups__name="Editor")
        self.fields["publisher"].queryset = User.objects.filter(
            groups__name="Publisher"
        )

    class Meta:
        model = Blog
        fields = [
            "title",
            "category",
            "content",
            "image",
            "author",
            "editor",
            "publisher",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter blog title"}
            ),
            "category": forms.Select(attrs={"class": "form-control"}),
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Enter blog content...",
                }
            ),
            "image": forms.FileInput(attrs={"class": "form-control-file"}),
            "author": forms.Select(attrs={"class": "form-control"}),
            "editor": forms.Select(attrs={"class": "form-control"}),
            "publisher": forms.Select(attrs={"class": "form-control"}),
        }
