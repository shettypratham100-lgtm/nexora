from django.contrib import admin

from .models import ResumeAnalysis


@admin.register(ResumeAnalysis)
class ResumeAnalysisAdmin(admin.ModelAdmin):

    list_display = ("user", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "user__email")
    readonly_fields = ("ai_recommendations", "created_at")