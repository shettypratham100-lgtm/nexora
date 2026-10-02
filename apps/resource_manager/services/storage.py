"""
storage.py

Two responsibilities:

1. STORAGE QUOTA
   Every user gets a fixed storage allowance
   (settings.USER_STORAGE_LIMIT_GB). Usage is calculated
   from Resource.file_size, which is captured automatically
   at upload time (see Resource.save()).

   Trashed files still count against the quota until they
   are permanently purged -- the disk space isn't actually
   freed until then, so it wouldn't be honest to exclude
   them.

2. TRASH
   Deleting a Collection or Resource from the UI soft-deletes
   it (is_deleted=True, deleted_at=now) instead of removing
   it immediately. Anything older than
   settings.TRASH_RETENTION_DAYS is permanently purged by
   purge_expired_trash(), which is called opportunistically
   whenever the user visits the Trash page.
"""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from ..models import Collection, Resource


# ============================================================
# STORAGE QUOTA
# ============================================================

def get_storage_usage(user):
    """
    Returns a dict describing how much storage a user has
    used, out of their total allowance.

    Returns
    -------
    dict with keys:
        used_bytes, limit_bytes, used_gb, limit_gb,
        percent_used (0-100, capped), is_over_limit
    """

    limit_bytes = settings.USER_STORAGE_LIMIT_GB * (1024 ** 3)

    used_bytes = (
        Resource.objects
        .filter(collection__user=user)
        .exclude(file="")
        .values_list("file_size", flat=True)
    )

    used_bytes = sum(used_bytes)

    percent_used = min(
        round((used_bytes / limit_bytes) * 100, 1) if limit_bytes else 0,
        100,
    )

    return {
        "used_bytes": used_bytes,
        "limit_bytes": limit_bytes,
        "used_gb": round(used_bytes / (1024 ** 3), 2),
        "limit_gb": settings.USER_STORAGE_LIMIT_GB,
        "percent_used": percent_used,
        "is_over_limit": used_bytes >= limit_bytes,
    }


def has_room_for(user, incoming_file_size):
    """
    Returns True if uploading a file of the given size
    (bytes) would keep the user within their storage quota.
    """

    usage = get_storage_usage(user)

    return (usage["used_bytes"] + incoming_file_size) <= usage["limit_bytes"]


# ============================================================
# TRASH
# ============================================================

def move_resource_to_trash(resource):
    resource.is_deleted = True
    resource.deleted_at = timezone.now()
    resource.save(update_fields=["is_deleted", "deleted_at"])


def move_collection_to_trash(collection):
    """
    Soft-deletes a collection AND every resource inside it,
    so they all show up in Trash together and expire on the
    same timeline.
    """

    now = timezone.now()

    collection.is_deleted = True
    collection.deleted_at = now
    collection.save(update_fields=["is_deleted", "deleted_at"])

    collection.resources.filter(is_deleted=False).update(
        is_deleted=True,
        deleted_at=now,
    )


def restore_resource(resource):
    resource.is_deleted = False
    resource.deleted_at = None
    resource.save(update_fields=["is_deleted", "deleted_at"])


def restore_collection(collection):
    """
    Restores a collection. Resources that were trashed
    alongside it are restored too; resources the user
    trashed individually (while the collection stayed
    active) are left alone.
    """

    collection.is_deleted = False
    collection.deleted_at = None
    collection.save(update_fields=["is_deleted", "deleted_at"])

    collection.resources.filter(is_deleted=True).update(
        is_deleted=False,
        deleted_at=None,
    )


def purge_expired_trash(user):
    """
    Permanently deletes any trashed Collection/Resource
    belonging to `user` whose retention window has passed.

    Safe to call on every Trash page load -- cheap when
    there's nothing to purge, and Resource's post_delete
    signal already handles removing files from disk.
    """

    cutoff = timezone.now() - timedelta(days=settings.TRASH_RETENTION_DAYS)

    Resource.objects.filter(
        collection__user=user,
        is_deleted=True,
        deleted_at__lt=cutoff,
    ).delete()

    Collection.objects.filter(
        user=user,
        is_deleted=True,
        deleted_at__lt=cutoff,
    ).delete()
