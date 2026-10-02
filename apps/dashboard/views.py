from django.shortcuts import render, redirect
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count

from apps.resource_manager.models import Collection, Resource
from apps.resource_manager.services.storage import get_storage_usage
from apps.resume_analyzer.models import ResumeAnalysis

from .services import get_recent_activity


def home(request):

    if request.user.is_authenticated:
        return redirect("dashboard:dashboard")

    return render(request, "dashboard/landing.html")


@login_required
def dashboard(request):

    user = request.user

    # ------------------------------------------------------
    # STAT CARDS: Collections / Resources / Documents / Storage
    # ------------------------------------------------------

    resources_qs = Resource.objects.filter(
        collection__user=user,
        is_deleted=False,
    )

    total_collections = Collection.objects.filter(
        user=user,
        is_deleted=False,
    ).count()

    total_resources = resources_qs.count()

    # "Documents" = resources that are actual uploaded files
    # (PDF/DOCX/PPT/images), as opposed to external links.
    total_documents = resources_qs.exclude(file="").count()

    storage = get_storage_usage(user)

    # ------------------------------------------------------
    # RECENT RESOURCES (most recently added, any type)
    # ------------------------------------------------------

    recent_resources = resources_qs.select_related("collection").order_by("-created_at")[:5]

    # ------------------------------------------------------
    # RECENT ACTIVITY PREVIEW (same feed as the full page,
    # trimmed to a handful of entries for the dashboard card)
    # ------------------------------------------------------

    recent_activity_preview = get_recent_activity(user, limit=6)

    # ------------------------------------------------------
    # LATEST RESUME SCORE (kept -- useful, not AI-assistant)
    # ------------------------------------------------------

    latest_analysis = ResumeAnalysis.objects.filter(user=user).order_by("-created_at").first()
    latest_score = None

    if latest_analysis:
        try:
            latest_score = latest_analysis.ai_recommendations.get(
                "overall_resume_score", {}
            ).get("score")
        except AttributeError:
            latest_score = None

    # ------------------------------------------------------
    # THIS WEEK -- real, computed activity summary
    # (no chatbot, just honest numbers from the DB)
    # ------------------------------------------------------

    week_ago = timezone.now() - timedelta(days=7)

    uploads_this_week = resources_qs.filter(created_at__gte=week_ago).count()

    summarized_this_week = resources_qs.filter(
        created_at__gte=week_ago,
        ai_status=Resource.AIStatus.COMPLETED,
    ).count()

    top_collection = (
        Collection.objects.filter(user=user, is_deleted=False)
        .annotate(resource_count=Count("resources"))
        .order_by("-resource_count")
        .first()
    )

    context = {
        "total_collections": total_collections,
        "total_resources": total_resources,
        "total_documents": total_documents,
        "storage": storage,
        "recent_resources": recent_resources,
        "recent_activity_preview": recent_activity_preview,
        "latest_analysis": latest_analysis,
        "latest_score": latest_score,
        "uploads_this_week": uploads_this_week,
        "summarized_this_week": summarized_this_week,
        "top_collection": top_collection,
    }

    return render(
        request,
        "dashboard/dashboard.html",
        context,
    )


@login_required
def recent_activity(request):

    activity = get_recent_activity(request.user, limit=60)

    return render(
        request,
        "dashboard/recent_activity.html",
        {"activity": activity},
    )
