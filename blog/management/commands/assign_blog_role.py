from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError

from blog.models import Blog
from blog.tasks import send_role_assignment_notification_task


class Command(BaseCommand):
    help = "Assigns a user to a specific role (Author, Editor, or Publisher) on a blog post, triggering async notifications."

    def add_arguments(self, parser):
        parser.add_argument(
            "--blog-id", type=int, required=True, help="ID of the blog post"
        )
        parser.add_argument(
            "--group",
            type=str,
            required=True,
            choices=["Author", "Editor", "Publisher"],
            help="User group/role to assign",
        )
        parser.add_argument(
            "--email", type=str, required=True, help="Email of the user to assign"
        )

    def handle(self, *args, **options):
        blog_id = options["blog_id"]
        group_name = options["group"]
        email = options["email"]

        # 1. Validate Blog Exists
        try:
            blog = Blog.objects.get(pk=blog_id)
        except Blog.DoesNotExist:
            raise CommandError(f"Blog post with ID {blog_id} does not exist.")

        # 2. Validate Group
        if group_name not in ["Author", "Editor", "Publisher"]:
            raise CommandError(
                f"Invalid group. Allowed choices are: Author, Editor, Publisher."
            )

        # 3. Validate User Exists
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise CommandError(f"User with email '{email}' does not exist.")
        except User.MultipleObjectsReturned:
            raise CommandError(f"Multiple users exist with email '{email}'.")

        # 4. Validate User belongs to the specified Group
        if not user.groups.filter(name=group_name).exists():
            raise CommandError(
                f"User '{user.username}' does not belong to the '{group_name}' group."
            )

        # Map group to model attribute
        role_attr = group_name.lower()
        old_user = getattr(blog, role_attr)

        # 5. Validate No Duplicate Assignment
        if old_user == user:
            raise CommandError(
                f"User '{user.username}' is already assigned as {group_name} on this blog."
            )

        # 6. Notification and Database update sequencing:
        # A. Send unassignment notification first to the old user (if present)
        if old_user:
            send_role_assignment_notification_task.delay(
                old_user.id, blog.id, group_name, is_unassignment=True
            )

        # B. Update the database
        setattr(blog, role_attr, user)
        blog.save()

        # C. Send assignment notification to the new user
        send_role_assignment_notification_task.delay(
            user.id, blog.id, group_name, is_unassignment=False
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully assigned '{user.username}' as {group_name} to blog post '{blog.title}'."
            )
        )
