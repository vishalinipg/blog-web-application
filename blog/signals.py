from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from .models import Blog


def create_groups_and_permissions(sender, **kwargs):
    """
    Automatically creates the Author, Editor, and Publisher user groups
    and assigns them the appropriate Blog CRUD permissions post migration.
    """
    # Force creation of default model permissions for the blog app
    for app_config in kwargs.get("app_configs", []):
        if app_config.name == "blog":
            create_permissions(app_config, verbosity=0)

    content_type = ContentType.objects.get_for_model(Blog)

    # Fetch standard Django CRUD permissions for the Blog model
    try:
        view_blog = Permission.objects.get(
            codename="view_blog", content_type=content_type
        )
        add_blog = Permission.objects.get(
            codename="add_blog", content_type=content_type
        )
        change_blog = Permission.objects.get(
            codename="change_blog", content_type=content_type
        )
        delete_blog = Permission.objects.get(
            codename="delete_blog", content_type=content_type
        )
    except Permission.DoesNotExist:
        return

    # Define dynamic mapping of groups to permissions list
    groups_setup = {
        "Author": [view_blog, add_blog],
        "Editor": [view_blog, add_blog, change_blog],
        "Publisher": [view_blog, add_blog, change_blog, delete_blog],
    }

    # Iterate and assign permissions to groups
    for group_name, perms in groups_setup.items():
        group, created = Group.objects.get_or_create(name=group_name)
        group.permissions.set(perms)
        group.save()
