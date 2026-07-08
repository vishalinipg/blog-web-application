from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """
    Custom authentication backend that allows authenticating users
    using their email address in a case-insensitive manner.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get("email")

        if username:
            try:
                # Query user by email in a case-insensitive lookup
                user = UserModel.objects.get(email__iexact=username)
            except UserModel.DoesNotExist:
                return None
            else:
                if user.check_password(password) and self.user_can_authenticate(user):
                    return user
        return None
