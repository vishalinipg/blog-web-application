from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse


class AjaxLoginRequiredMixin:
    """
    Custom mixin to enforce user authentication.
    Intercepts unauthenticated requests:
    - Returns a 401 Unauthorized JSON response for AJAX requests.
    - Redirects standard page requests to the login page.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            if (
                request.headers.get("x-requested-with") == "XMLHttpRequest"
                or request.path.startswith("/blogs/datatable/")
            ):
                return JsonResponse(
                    {"success": False, "message": "Authentication required."},
                    status=401,
                )
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        return super().dispatch(request, *args, **kwargs)


class AjaxPermissionRequiredMixin:
    """
    Custom mixin to enforce granular permission checks.
    Intercepts unauthorized requests:
    - Returns a 403 Forbidden JSON response for AJAX requests.
    - Raises a PermissionDenied (403 HTML) exception for standard page requests.
    """

    permission_required = None

    def get_permission_required(self):
        if self.permission_required is None:
            raise NotImplementedError(
                "Mixin requires the 'permission_required' attribute to be defined."
            )
        if isinstance(self.permission_required, str):
            return (self.permission_required,)
        return self.permission_required

    def has_permission(self, request):
        perms = self.get_permission_required()
        return request.user.has_perms(perms)

    def dispatch(self, request, *args, **kwargs):
        # First ensure the user is logged in
        if not request.user.is_authenticated:
            if (
                request.headers.get("x-requested-with") == "XMLHttpRequest"
                or request.path.startswith("/blogs/datatable/")
            ):
                return JsonResponse(
                    {"success": False, "message": "Authentication required."},
                    status=401,
                )
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)

        if not self.has_permission(request):
            if (
                request.headers.get("x-requested-with") == "XMLHttpRequest"
                or request.path.startswith("/blogs/datatable/")
            ):
                return JsonResponse(
                    {"success": False, "message": "Permission denied."}, status=403
                )
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
