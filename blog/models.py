import os

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models


def validate_not_only_whitespace(value):
    """
    Ensures that the input does not consist only of spaces or whitespace.
    """
    if not value or not value.strip():
        raise ValidationError(
            "This field cannot be empty or consist only of whitespace."
        )


def validate_blog_image(field_file):
    """
    Ensures uploaded images do not exceed size limit (5MB) and use valid extensions.
    """
    if not field_file:
        return

    # 1. File size check (5MB limit)
    max_size_bytes = 5 * 1024 * 1024
    if field_file.size > max_size_bytes:
        raise ValidationError("Image file size must be under 5MB.")

    # 2. Extension check
    ext = os.path.splitext(field_file.name)[1].lower()
    valid_extensions = [".jpg", ".jpeg", ".png", ".webp"]
    if ext not in valid_extensions:
        raise ValidationError(
            f"Unsupported file extension '{ext}'. Allowed extensions are: {', '.join(valid_extensions)}."
        )


class Category(models.TextChoices):
    PYTHON = "Python", "Python"
    DJANGO = "Django", "Django"
    POWERBI = "PowerBI", "PowerBI"
    SCRAPY = "Scrapy", "Scrapy"


class Blog(models.Model):
    """
    Blog Model representing article entries in the web application.
    Contains content fields, category definitions, auto-managed timestamps,
    and a media field for cover images.
    """

    title = models.CharField(
        max_length=255,
        validators=[validate_not_only_whitespace],
        verbose_name="Title",
        help_text="Enter the title of the blog post.",
    )
    content = models.TextField(
        validators=[validate_not_only_whitespace],
        verbose_name="Content",
        help_text="Enter the body content of the blog post.",
    )
    image = models.ImageField(
        upload_to="blogs/",
        blank=True,
        null=True,
        validators=[validate_blog_image],
        verbose_name="Image",
        help_text="Upload a cover image for the blog post.",
    )
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        verbose_name="Category",
        help_text="Select a programming or analytics category.",
    )
    tags = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Tags",
        help_text="Enter comma-separated tags.",
    )
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authored_blogs",
        verbose_name="Author",
        help_text="Select the author of the blog post.",
    )
    editor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="edited_blogs",
        verbose_name="Editor",
        help_text="Select the editor of the blog post.",
    )
    publisher = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="published_blogs",
        verbose_name="Publisher",
        help_text="Select the publisher of the blog post.",
    )
    publish = models.BooleanField(
        default=True, verbose_name="Publish", help_text="Check to make the post public."
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    @property
    def tags_list(self):
        """
        Parses the tags string into a list of clean tag names.
        """
        if self.tags:
            return [t.strip() for t in self.tags.split(",") if t.strip()]
        return []

    class Meta:
        verbose_name = "Blog"
        verbose_name_plural = "Blogs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["category"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.category})"
