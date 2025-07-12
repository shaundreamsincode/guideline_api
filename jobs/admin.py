from django.contrib import admin

from .models import Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("event_id", "title", "status", "created_at", "updated_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "guideline_text", "summary")
    readonly_fields = ("event_id", "created_at", "updated_at")
    ordering = ("-created_at",)
