from django.contrib import admin

from .models import Blog


@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "created_at", "updated_at")
    list_filter = ("category", "created_at")
    search_fields = ("title", "content")
    date_hierarchy = "created_at"
