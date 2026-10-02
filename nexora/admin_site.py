from django.contrib.admin import AdminSite
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta


from django.contrib.auth import get_user_model
from apps.resource_manager.models import Resource
from apps.resume_analyzer.models import ResumeAnalysis
from apps.document_toolkit.models import ToolJob

class NexoraAdminSite(AdminSite):

    site_header = "Nexora Administration"
    site_title = "Nexora Admin"
    index_title = "Dashboard"

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["nexora_stats"] = self.get_dashboard_stats()
        return super().index(request, extra_context)

    def get_dashboard_stats(self):

        User = get_user_model()
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)

        total_users = User.objects.count()
        total_resources = Resource.objects.filter(is_deleted=False).count()
        total_analyses = ResumeAnalysis.objects.count()
        total_jobs = ToolJob.objects.count()

        new_users_today = User.objects.filter(date_joined__gte=today_start).count()
        new_users_week = User.objects.filter(date_joined__gte=week_start).count()
        new_resources_week = Resource.objects.filter(created_at__gte=week_start,is_deleted=False).count()

        ai_pending = Resource.objects.filter(ai_status=Resource.AIStatus.PENDING).count()
        ai_processing = Resource.objects.filter(ai_status=Resource.AIStatus.PROCESSING).count()
        ai_completed = Resource.objects.filter(ai_status=Resource.AIStatus.COMPLETED).count()
        ai_failed = Resource.objects.filter(ai_status=Resource.AIStatus.FAILED).count()

        storage_by_type = list(
            Resource.objects.filter(is_deleted=False)
            .values("resource_type")
            .annotate(
                total_bytes=Sum("file_size"),
                count=Count("id")
            )
            .order_by("-total_bytes")
        )

        for item in storage_by_type:

            item["size_display"] = self._format_bytes(
                item["total_bytes"] or 0
            )

        total_storage_bytes = sum(r["total_bytes"] or 0 for r in storage_by_type)

        analyses_today = ResumeAnalysis.objects.filter(created_at__gte=today_start).count()
        analyses_week = ResumeAnalysis.objects.filter(created_at__gte=week_start).count()

        ats_scores = []
        for a in ResumeAnalysis.objects.all().only("ai_recommendations"):
            try:
                score = a.ai_recommendations.get("ats_score", {}).get("score")
                if isinstance(score, (int, float)):
                    ats_scores.append(score)
            except (AttributeError, TypeError):
                continue

        avg_ats = round(sum(ats_scores) / len(ats_scores), 1) if ats_scores else None

        toolkit_by_type = list(
            ToolJob.objects.values("tool_type")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        toolkit_success = ToolJob.objects.filter(status=ToolJob.Status.SUCCESS).count()
        toolkit_failed = ToolJob.objects.filter(status=ToolJob.Status.FAILED).count()

        recent_failed_resources = Resource.objects.filter(
            ai_status=Resource.AIStatus.FAILED
        ).order_by("-created_at")[:5]

        recent_failed_jobs = ToolJob.objects.filter(
            status=ToolJob.Status.FAILED
        ).order_by("-created_at")[:5]

        return {
            "total_users": total_users,
            "total_resources": total_resources,
            "total_analyses": total_analyses,
            "total_jobs": total_jobs,
            "new_users_today": new_users_today,
            "new_users_week": new_users_week,
            "new_resources_week": new_resources_week,
            "ai_pending": ai_pending,
            "ai_processing": ai_processing,
            "ai_completed": ai_completed,
            "ai_failed": ai_failed,
            "storage_by_type": storage_by_type,
            "total_storage_display": self._format_bytes(total_storage_bytes),
            "analyses_today": analyses_today,
            "analyses_week": analyses_week,
            "avg_ats": avg_ats,
            "toolkit_by_type": toolkit_by_type,
            "toolkit_success": toolkit_success,
            "toolkit_failed": toolkit_failed,
            "recent_failed_resources": recent_failed_resources,
            "recent_failed_jobs": recent_failed_jobs,
        }

    @staticmethod
    def _format_bytes(num_bytes):
        if not num_bytes:
            return "0 MB"
        mb = num_bytes / (1024 * 1024)
        if mb < 1024:
            return f"{mb:.1f} MB"
        return f"{mb / 1024:.2f} GB"