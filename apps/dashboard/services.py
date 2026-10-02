from django.db.models import F
from django.urls import reverse

from apps.resource_manager.models import Collection, Resource
from apps.resume_analyzer.models import ResumeAnalysis
from apps.document_toolkit.models import ToolJob


# How many records of EACH activity kind to pull before merging
# and trimming to the final feed length. Keep generous so a burst
# of activity in one category doesn't crowd out the others.
ACTIVITY_FETCH_LIMIT = 25


def get_recent_activity(user, limit=60):
    """
    Builds the unified activity feed for a user: every file
    uploaded, every file or collection sent to Trash, every
    collection created, every Document Toolkit conversion, and
    every resume analysis -- merged into one list, newest first.

    Used by both the full "Recent Activity" page and the
    dashboard's activity preview widget, so both stay in sync.
    """

    activity = []

    # ------------------------------------------------------
    # FILES UPLOADED / ADDED
    # ------------------------------------------------------

    resources = Resource.objects.filter(
        collection__user=user,
        is_deleted=False,
    ).select_related("collection").order_by("-created_at")[:ACTIVITY_FETCH_LIMIT]

    for resource in resources:
        activity.append({
            "type": "resource",
            "icon": "bi-file-earmark-plus",
            "title": resource.title,
            "meta": f"Added to {resource.collection.name}",
            "timestamp": resource.created_at,
            "url": reverse("resource_manager:view_resource", args=[resource.pk]),
        })

    # ------------------------------------------------------
    # FILES DELETED (moved to Trash)
    #
    # Excludes files that were only trashed because their
    # whole collection was deleted at the same moment -- that
    # already shows up as a single "Collection deleted" entry
    # below, so we don't want dozens of duplicate rows.
    # ------------------------------------------------------

    deleted_resources = Resource.objects.filter(
        collection__user=user,
        is_deleted=True,
    ).exclude(
        collection__is_deleted=True,
        deleted_at=F("collection__deleted_at"),
    ).select_related("collection").order_by("-deleted_at")[:ACTIVITY_FETCH_LIMIT]

    for resource in deleted_resources:
        activity.append({
            "type": "resource_deleted",
            "icon": "bi-trash3",
            "title": resource.title,
            "meta": f"Moved to Trash from {resource.collection.name}",
            "timestamp": resource.deleted_at,
            "url": reverse("resource_manager:trash"),
        })

    # ------------------------------------------------------
    # COLLECTIONS CREATED
    # ------------------------------------------------------

    collections = Collection.objects.filter(
        user=user,
        is_deleted=False,
    ).order_by("-created_at")[:ACTIVITY_FETCH_LIMIT]

    for collection in collections:
        activity.append({
            "type": "collection",
            "icon": "bi-folder-plus",
            "title": collection.name,
            "meta": "Collection created",
            "timestamp": collection.created_at,
            "url": reverse("resource_manager:collection_detail", args=[collection.pk]),
        })

    # ------------------------------------------------------
    # COLLECTIONS DELETED (moved to Trash)
    # ------------------------------------------------------

    deleted_collections = Collection.objects.filter(
        user=user,
        is_deleted=True,
    ).order_by("-deleted_at")[:ACTIVITY_FETCH_LIMIT]

    for collection in deleted_collections:
        activity.append({
            "type": "collection_deleted",
            "icon": "bi-folder-x",
            "title": collection.name,
            "meta": "Collection moved to Trash",
            "timestamp": collection.deleted_at,
            "url": reverse("resource_manager:trash"),
        })

    # ------------------------------------------------------
    # DOCUMENT TOOLKIT CONVERSIONS
    # (merge, split, compress, watermark, rotate, PDF<->DOCX,
    # PPT to PDF, image to PDF, create PDF -- every run shows
    # up here, not just a handful of tool types.)
    # ------------------------------------------------------

    tool_jobs = ToolJob.objects.filter(
        user=user,
        status=ToolJob.Status.SUCCESS,
    ).order_by("-created_at")[:ACTIVITY_FETCH_LIMIT]

    for job in tool_jobs:
        activity.append({
            "type": "conversion",
            "icon": "bi-magic",
            "title": job.summary or job.get_tool_type_display(),
            "meta": f"Document Toolkit \u2014 {job.get_tool_type_display()}",
            "timestamp": job.created_at,
            "url": job.output_file.url if job.output_file else reverse("document_toolkit:home"),
        })

    # ------------------------------------------------------
    # RESUME ANALYSES
    # ------------------------------------------------------

    analyses = ResumeAnalysis.objects.filter(user=user).order_by("-created_at")[:ACTIVITY_FETCH_LIMIT]

    for analysis in analyses:
        score = None
        try:
            score = analysis.ai_recommendations.get("overall_resume_score", {}).get("score")
        except AttributeError:
            score = None

        activity.append({
            "type": "resume",
            "icon": "bi-file-earmark-person",
            "title": f"Resume analyzed \u2014 score {score}" if score is not None else "Resume analyzed",
            "meta": "Resume Analyzer",
            "timestamp": analysis.created_at,
            "url": reverse("resume_result", args=[analysis.pk]),
        })

    # Every entry above has a real timestamp, so a single sort
    # interleaves all six kinds of activity correctly.
    activity.sort(key=lambda item: item["timestamp"], reverse=True)

    return activity[:limit]
