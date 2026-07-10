from django.contrib.auth.models import User
from rest_framework import serializers

from blog.models import Blog


class BlogSerializer(serializers.ModelSerializer):
    """
    Serializer mapping to the Blog model, including validation rules
    to ensure author, editor, and publisher ForeignKeys are assigned
    to users belonging to the correct Django Groups.
    """

    tags_list = serializers.ReadOnlyField()

    author = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(groups__name="Author"),
        required=False,
        allow_null=True,
    )
    editor = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(groups__name="Editor"),
        required=False,
        allow_null=True,
    )
    publisher = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(groups__name="Publisher"),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Blog
        fields = [
            "id",
            "title",
            "content",
            "image",
            "category",
            "tags",
            "tags_list",
            "author",
            "editor",
            "publisher",
            "publish",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "tags_list", "created_at", "updated_at"]
