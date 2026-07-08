from django.apps import AppConfig
from django.db.models.signals import post_migrate


class BlogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "blog"

    def ready(self):
        # Local import here is strictly required to prevent AppRegistryNotReady
        # circular loading exception when django.contrib.auth models are loaded.
        from .signals import create_groups_and_permissions

        post_migrate.connect(create_groups_and_permissions, sender=self)