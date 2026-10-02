from django.contrib import admin

from .models import Collection, Resource, RecentSearch
from services.ai.ai_processor import process_resource_by_id
import threading


class ResourceInline(admin.TabularInline):
    model = Resource
    extra = 0
    fields = ("title", "resource_type", "ai_status", "is_starred", "is_deleted")
    readonly_fields = ("title", "resource_type")
    show_change_link = True


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):

    list_display = ("name", "user", "is_starred", "is_deleted", "created_at")
    list_filter = ("is_starred", "is_deleted", "created_at")
    search_fields = ("name", "user__username", "user__email")
    inlines = [ResourceInline]


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):

    list_display = (
        "title", "collection", "resource_type", "ai_status",
        "is_starred", "is_deleted", "file_size", "created_at",
    )
    list_filter = ("ai_status", "resource_type", "is_starred", "is_deleted")
    search_fields = ("title", "collection__name", "collection__user__username")
    readonly_fields = ("last_error", "file_size")

    actions = ["retry_ai_processing"]

    @admin.action(description="Retry AI processing for selected (failed) resources")
    def retry_ai_processing(self, request, queryset):
        failed = queryset.filter(ai_status=Resource.AIStatus.FAILED)
        for resource in failed:
            resource.ai_status = Resource.AIStatus.PENDING
            resource.save(update_fields=["ai_status"])
            threading.Thread(target=process_resource_by_id, args=(resource.pk,)).start()
        self.message_user(request, f"Retrying AI processing for {failed.count()} resource(s).")


@admin.register(RecentSearch)
class RecentSearchAdmin(admin.ModelAdmin):

    list_display = ("query", "user", "searched_at")
    search_fields = ("query", "user__username")
    list_filter = ("searched_at",)