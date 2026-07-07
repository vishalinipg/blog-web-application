import os
from urllib.parse import urlencode

from ajax_datatable.views import AjaxDatatableView
from django.http import HttpResponse, JsonResponse, QueryDict
from django.http.multipartparser import MultiPartParser
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.datastructures import MultiValueDict
from django.utils.text import Truncator
from django.views import View
from django.views.generic import DetailView, TemplateView

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import Group, User
from django.contrib.auth.views import LoginView, LogoutView

from .forms import BlogForm, EmailAuthenticationForm, SignupForm
from .mixins import AjaxLoginRequiredMixin, AjaxPermissionRequiredMixin
from .models import Blog


class SignupView(View):
    """
    Class-Based View to handle user registration.
    Renders signup.html on GET, processes input and assigns selected group on POST.
    """

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("blog:list")
        form = SignupForm()
        return render(request, "blog/signup.html", {"form": form})

    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("blog:list")
        form = SignupForm(request.POST)
        if form.is_valid():
            full_name = form.cleaned_data["full_name"]
            email = form.cleaned_data["email"]
            group_name = form.cleaned_data["group"]
            password = form.cleaned_data["password"]

            # Split full name on the first space intelligently
            name_parts = full_name.strip().split(" ", 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ""

            # Create User
            user = User.objects.create_user(
                username=email,  # Set email as username for EmailBackend
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )

            # Assign selected group
            try:
                group = Group.objects.get(name=group_name)
                user.groups.add(group)
            except Group.DoesNotExist:
                pass

            messages.success(request, "Registration successful! Please log in.")
            return redirect("blog:login")
        else:
            return render(request, "blog/signup.html", {"form": form})


class BlogListView(AjaxLoginRequiredMixin, AjaxPermissionRequiredMixin, TemplateView):
    permission_required = "blog.view_blog"
    """
    Renders the blog list dashboard template, providing a blank BlogForm instance
    in the context for the asynchronous create modal.
    """

    template_name = "blog/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = BlogForm()
        return context


class BlogAjaxDatatableView(
    AjaxLoginRequiredMixin, AjaxPermissionRequiredMixin, AjaxDatatableView
):
    permission_required = "blog.view_blog"
    """
    Server-side controller for the django-ajax-datatable interface.
    Handles searching, pagination, sorting, and returns structured JSON responses.
    """

    model = Blog
    title = "Blogs"
    initial_order = [["created_at", "desc"]]
    length_menu = [[10, 25, 50, -1], [10, 25, 50, "All"]]
    show_column_filters = False

    column_defs = [
        {"name": "id", "visible": False},
        {
            "name": "title",
            "title": "TITLE",
            "visible": True,
            "searchable": True,
            "orderable": True,
        },
        {
            "name": "image",
            "title": "IMAGES",
            "visible": True,
            "placeholder": True,
            "searchable": False,
            "orderable": False,
        },
        {
            "name": "category",
            "title": "CATEGORY",
            "visible": True,
            "searchable": True,
            "orderable": True,
        },
        {
            "name": "tags",
            "title": "TAGS",
            "visible": True,
            "placeholder": True,
            "searchable": False,
            "orderable": False,
        },
        {
            "name": "created_at",
            "title": "CREATED AT",
            "visible": True,
            "searchable": False,
            "orderable": True,
        },
        {
            "name": "actions",
            "title": "ACTION",
            "placeholder": True,
            "searchable": False,
            "orderable": False,
        },
    ]

    def get_initial_queryset(self, request=None):
        queryset = super().get_initial_queryset(request)
        if request:
            # Retrieve the comma-separated categories list passed by extra_data
            categories_str = request.POST.get("categories", "") or request.GET.get(
                "categories", ""
            )
            if categories_str:
                categories_list = [
                    c.strip() for c in categories_str.split(",") if c.strip()
                ]
                if categories_list:
                    queryset = queryset.filter(category__in=categories_list)
        return queryset

    def customize_row(self, row, obj):
        # Render the image column as a thumbnail matching the layout
        if obj.image:
            row["image"] = (
                f'<img src="{obj.image.url}" class="img-fluid rounded border" style="max-height: 50px; width: 80px; object-fit: cover;">'
            )
        else:
            row["image"] = '<span class="text-muted small">No Image</span>'

        # Render dynamic tag badges from the database record
        row["tags"] = "".join(
            [
                f'<span class="badge badge-light border text-secondary font-weight-normal px-2 py-1 mr-1">{tag}</span>'
                for tag in obj.tags_list
            ]
        )

        # Format created_at to MM/DD/YYYY
        row["created_at"] = obj.created_at.strftime("%m/%d/%Y")

        # Dynamic URL reverse resolutions from project patterns routing
        detail_url = reverse("blog:detail", kwargs={"pk": obj.id})
        edit_url = reverse("blog:edit", kwargs={"pk": obj.id})
        delete_url = reverse("blog:delete", kwargs={"pk": obj.id})

        # Generate action buttons dynamically based on user permissions
        user = self.request.user
        can_view = user.has_perm("blog.view_blog")
        can_edit = user.has_perm("blog.change_blog")
        can_delete = user.has_perm("blog.delete_blog")

        actions_html = '<div class="text-center">'
        if can_view:
            actions_html += f"""
                <a href="{detail_url}" class="action-icon-link" title="View Detail">
                    <i class="fas fa-eye"></i>
                </a>
            """
        if can_edit:
            actions_html += f"""
                <a href="#" class="action-icon-link edit-blog-btn" 
                   data-id="{obj.id}" 
                   data-url="{edit_url}" 
                   title="Edit Blog">
                    <i class="fas fa-pencil-alt"></i>
                </a>
            """
        if can_delete:
            actions_html += f"""
                <a href="#" class="action-icon-link delete-blog-btn delete-icon" 
                   data-id="{obj.id}" 
                   data-url="{delete_url}" 
                   title="Delete Blog">
                    <i class="fas fa-trash"></i>
                </a>
            """
        actions_html += "</div>"
        row["actions"] = actions_html
        return row


class BlogCreateView(AjaxLoginRequiredMixin, AjaxPermissionRequiredMixin, View):
    permission_required = "blog.add_blog"
    """
    Handles rendering the full-page creation form (GET)
    and processing the creation request (POST) with tag formatting.
    """

    def get(self, request, *args, **kwargs):
        form = BlogForm()
        return render(request, "blog/create.html", {"form": form})

    def post(self, request, *args, **kwargs):
        form = BlogForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            # Retrieve tags lists and concatenate as comma-separated values
            tags_list = request.POST.getlist("tags")
            obj.tags = ", ".join(tags_list)
            obj.save()
            redirect_url = reverse("blog:list")
            query_string = urlencode({"success": 1})
            return redirect(f"{redirect_url}?{query_string}")
        else:
            return render(request, "blog/create.html", {"form": form})


class BlogUpdateView(AjaxLoginRequiredMixin, AjaxPermissionRequiredMixin, View):
    permission_required = "blog.change_blog"
    """
    Class-Based View to retrieve blog details (GET) and save changes (POST)
    asynchronously using form validations.
    """

    def get(self, request, pk, *args, **kwargs):
        try:
            obj = Blog.objects.get(pk=pk)
        except Blog.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "Blog post not found."}, status=404
            )
        data = {
            "id": obj.id,
            "title": obj.title,
            "category": obj.category,
            "content": obj.content,
            "tags": obj.tags_list,  # Return tags list for select2 pre-population
            "publish": obj.publish,
            "image_url": obj.image.url if obj.image else "",
            "author": obj.author_id,
            "editor": obj.editor_id,
            "publisher": obj.publisher_id,
        }
        return JsonResponse({"success": True, "data": data})

    def put(self, request, pk, *args, **kwargs):
        try:
            obj = Blog.objects.get(pk=pk)
        except Blog.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "Blog post not found."}, status=404
            )

        # Parse multipart/form-data for PUT requests
        if request.content_type.startswith("multipart/form-data"):
            put_data, put_files = MultiPartParser(
                request.META, request, request.upload_handlers
            ).parse()
        else:
            put_data = QueryDict(request.body)
            put_files = MultiValueDict()

        form = BlogForm(put_data, put_files, instance=obj)
        if form.is_valid():
            edit_obj = form.save(commit=False)
            # Extract and join multiselect tags array from the parsed PUT data
            tags_list = put_data.getlist("tags")
            edit_obj.tags = ", ".join(tags_list)

            # Map publish state checkbox explicitly from the parsed PUT data
            edit_obj.publish = (
                "publish" in put_data or put_data.get("publish") == "true"
            )

            edit_obj.save()
            return JsonResponse(
                {"success": True, "message": "Blog post updated successfully!"}
            )
        else:
            errors = {
                field: [str(err) for err in errs] for field, errs in form.errors.items()
            }
            return JsonResponse({"success": False, "errors": errors}, status=400)


class BlogDetailView(AjaxLoginRequiredMixin, AjaxPermissionRequiredMixin, DetailView):
    permission_required = "blog.view_blog"
    """
    Class-Based View to display the detail layout of a single blog post.
    Renders templates/blog/detail.html.
    """

    model = Blog
    template_name = "blog/detail.html"
    context_object_name = "blog"


class BlogDeleteView(AjaxLoginRequiredMixin, AjaxPermissionRequiredMixin, View):
    permission_required = "blog.delete_blog"
    """
    Class-Based View to handle asynchronous deletion of a Blog post.
    Deletes the associated media file from disk to prevent storage leakage,
    and removes the record from the database.
    """

    def delete(self, request, pk, *args, **kwargs):
        try:
            obj = Blog.objects.get(pk=pk)
        except Blog.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "Blog post not found."}, status=404
            )

        # Delete image file from disk if it exists
        if obj.image:
            image_path = obj.image.path
            try:
                if os.path.exists(image_path):
                    os.remove(image_path)
            except Exception as e:
                # Log the exception or handle pass safely in production
                pass

        obj.delete()
        return JsonResponse(
            {"success": True, "message": "Blog post deleted successfully."}
        )
