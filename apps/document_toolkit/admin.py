from django.contrib import admin
from django.utils.html import format_html

from .models import ToolJob


@admin.register(ToolJob)
class ToolJobAdmin(admin.ModelAdmin):

    list_display = ("user", "tool_type", "status", "summary", "output_link", "created_at")
    list_filter = ("tool_type", "status", "created_at")
    search_fields = ("user__username", "summary")
    ordering = ("-created_at",)
    readonly_fields = ("error_message",)

    @admin.display(description="Output")
    def output_link(self, job):
        if job.output_file:
            return format_html('<a href="{}" target="_blank">Download</a>', job.output_file.url)
        return "—"