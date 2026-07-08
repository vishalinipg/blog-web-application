from django.contrib import messages
from django.contrib.auth.models import Group, User
from django.shortcuts import redirect, render
from django.views import View

from .forms import SignupForm


class SignupView(View):
    """
    Class-Based View to handle user registration.
    Renders signup.html on GET, processes input and assigns selected group on POST.
    """

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("blog:list")
        form = SignupForm()
        return render(request, "accounts/signup.html", {"form": form})

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
            return redirect("accounts:login")
        else:
            return render(request, "accounts/signup.html", {"form": form})
