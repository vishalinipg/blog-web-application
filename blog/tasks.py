import datetime
from celery import shared_task
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from .models import Blog


@shared_task
def send_weekly_author_submissions_email_task(author_id, start_date_str, end_date_str):
    """
    Renders and sends the weekly submission report email to a single author.
    """
    try:
        author = User.objects.get(pk=author_id)
    except User.DoesNotExist:
        return

    # Parse dates from ISO strings and ensure they are timezone aware
    start_date = timezone.datetime.fromisoformat(start_date_str)
    if timezone.is_naive(start_date):
        start_date = timezone.make_aware(start_date)
        
    end_date = timezone.datetime.fromisoformat(end_date_str)
    if timezone.is_naive(end_date):
        end_date = timezone.make_aware(end_date)

    # Fetch blogs authored by this user created in the previous calendar week
    blogs = Blog.objects.filter(
        author=author, created_at__gte=start_date, created_at__lte=end_date
    )
    blogs_count = blogs.count()

    context = {
        "author_name": author.get_full_name() or author.username,
        "blogs": blogs,
        "blogs_count": blogs_count,
        "start_date": start_date,
        "end_date": end_date,
    }

    # Render email contents using dedicated templates
    subject = "Weekly Blog Submission Report"
    text_content = render_to_string("emails/weekly_report.txt", context)
    html_content = render_to_string("emails/weekly_report.html", context)

    send_mail(
        subject=subject,
        message=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[author.email],
        html_message=html_content,
    )


@shared_task
def send_weekly_author_submissions_report():
    """
    Celery Beat task that runs every Monday at 6:00 AM.
    Identifies all authors, calculates previous calendar week date ranges,
    and dispatches individual report tasks asynchronously.
    """
    today = timezone.localtime(timezone.now()).date()

    # Calculate previous calendar week Monday to Sunday
    start_of_previous_week = today - datetime.timedelta(days=today.weekday() + 7)
    end_of_previous_week = start_of_previous_week + datetime.timedelta(days=6)

    # Convert to aware datetimes
    start_datetime = timezone.make_aware(
        datetime.datetime.combine(start_of_previous_week, datetime.time.min)
    )
    end_datetime = timezone.make_aware(
        datetime.datetime.combine(end_of_previous_week, datetime.time.max)
    )

    authors = User.objects.filter(groups__name="Author")
    for author in authors:
        send_weekly_author_submissions_email_task.delay(
            author.id, start_datetime.isoformat(), end_datetime.isoformat()
        )


@shared_task
def send_role_assignment_notification_task(user_id, blog_id, role, is_unassignment):
    """
    Asynchronously notifies a user when they are assigned to or removed from a blog role.
    """
    try:
        user = User.objects.get(pk=user_id)
        blog = Blog.objects.get(pk=blog_id)
    except (User.DoesNotExist, Blog.DoesNotExist):
        return

    context = {
        "user_name": user.get_full_name() or user.username,
        "role": role,
        "blog_title": blog.title,
    }

    if is_unassignment:
        subject = f"Removed as {role} from blog: {blog.title}"
        text_content = render_to_string("emails/role_unassignment.txt", context)
        html_content = render_to_string("emails/role_unassignment.html", context)
    else:
        subject = f"Assigned as {role} for blog: {blog.title}"
        text_content = render_to_string("emails/role_assignment.txt", context)
        html_content = render_to_string("emails/role_assignment.html", context)

    send_mail(
        subject=subject,
        message=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_content,
    )


@shared_task
def send_password_reset_email_async(
    subject_template_name,
    email_template_name,
    context_dict,
    from_email,
    to_email,
    html_email_template_name=None,
):
    """
    Renders and sends password reset email asynchronously via Celery worker.
    """
    try:
        user = User.objects.get(pk=context_dict["user_id"])
    except User.DoesNotExist:
        return

    context = dict(context_dict)
    context["user"] = user

    subject = render_to_string(subject_template_name, context)
    subject = "".join(subject.splitlines())
    text_content = render_to_string(email_template_name, context)

    html_content = None
    if html_email_template_name:
        html_content = render_to_string(html_email_template_name, context)

    send_mail(
        subject=subject,
        message=text_content,
        from_email=from_email,
        recipient_list=[to_email],
        html_message=html_content,
    )
