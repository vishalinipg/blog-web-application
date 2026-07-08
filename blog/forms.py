from django import forms
from django.contrib.auth.models import User

from .models import Blog


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
