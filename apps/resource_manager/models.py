from django.db import models
from django.conf import settings
import os


# =====================================================
# COLLECTION MODEL
# =====================================================
# A collection is used to organize resources.
#
# Examples:
# - Semester 5
# - Python
# - Placement Preparation
# - AI
# =====================================================

class Collection(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="collections"
    )

    name = models.CharField(
        max_length=100
    )

    description = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    # ------------------------------------------------
    # STARRED
    # ------------------------------------------------

    is_starred = models.BooleanField(
        default=False
    )

    # ------------------------------------------------
    # TRASH (soft delete)
    #
    # Deleting a collection from the UI no longer removes
    # it immediately -- it's moved to Trash and permanently
    # purged after 30 days (see services/trash.py).
    # ------------------------------------------------

    is_deleted = models.BooleanField(
        default=False
    )

    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:

        ordering = ["-created_at"]

        unique_together = ("user", "name")

    def __str__(self):

        return self.name


# =====================================================
# RESOURCE MODEL
# =====================================================
# Stores uploaded files and external links.
#
# Supported:
# - PDF
# - DOCX
# - PPT
# - Images
# - YouTube
# - Google Drive
# - Websites
# =====================================================

class Resource(models.Model):

    class ResourceType(models.TextChoices):

        PDF = "PDF", "PDF"

        DOCX = "DOCX", "DOCX"

        PPT = "PPT", "PowerPoint"

        IMAGE = "IMAGE", "Image"

        YOUTUBE = "YOUTUBE", "YouTube"

        WEBSITE = "WEBSITE", "Website"

        DRIVE = "DRIVE", "Google Drive"


    class AIStatus(models.TextChoices):

        PENDING = "PENDING", "Pending"

        PROCESSING = "PROCESSING", "Processing"

        COMPLETED = "COMPLETED", "Completed"

        FAILED = "FAILED", "Failed"


    collection = models.ForeignKey(
        Collection,
        on_delete=models.CASCADE,
        related_name="resources"
    )

    title = models.CharField(
        max_length=255
    )

    description = models.TextField(
        blank=True
    )

    resource_type = models.CharField(
        max_length=20,
        choices=ResourceType.choices
    )

    file = models.FileField(
        upload_to="resources/",
        blank=True,
        null=True
    )

    external_url = models.URLField(
        blank=True,
        null=True
    )

    summary = models.TextField(
        blank=True
    )

    keywords = models.TextField(
        blank=True
    )

    ai_status = models.CharField(
        max_length=20,
        choices=AIStatus.choices,
        default=AIStatus.PENDING
    )

    retry_count = models.PositiveSmallIntegerField(
        default=0,
        help_text="Number of AI processing retry attempts."
    )

    last_error = models.TextField(
        blank=True,
        default="",
        help_text="Stores the last AI processing error for debugging."
    )

    # ------------------------------------------------
    # FILE SIZE (bytes)
    #
    # Captured at upload time so storage-quota checks
    # don't have to hit the filesystem for every resource
    # on every page load.
    # ------------------------------------------------

    file_size = models.PositiveBigIntegerField(
        default=0
    )

    # ------------------------------------------------
    # STARRED
    # ------------------------------------------------

    is_starred = models.BooleanField(
        default=False
    )

    # ------------------------------------------------
    # TRASH (soft delete)
    #
    # Deleting a resource from the UI no longer removes
    # it immediately -- it's moved to Trash and
    # permanently purged after 30 days.
    # ------------------------------------------------

    is_deleted = models.BooleanField(
        default=False
    )

    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = ["-created_at"]

    def __str__(self):

        return self.title
    
    def save(self, *args, **kwargs):

        # ------------------------------------------------
        # Capture the uploaded file's size (bytes) so
        # storage-quota checks stay a cheap DB aggregate
        # instead of a filesystem walk.
        # ------------------------------------------------

        if self.file:

            try:
                self.file_size = self.file.size
            except (OSError, ValueError):
                pass

        # ==================================================
        # CUSTOM SAVE METHOD
        # ==================================================
        #
        # Django's default FileField behavior:
        #
        # When a user uploads a new file while editing
        # an existing resource, Django saves the new file
        # but DOES NOT delete the previous file from the
        # media folder.
        #
        # Example:
        #
        # Before Edit:
        #     media/resources/flutter_notes.pdf
        #
        # User uploads:
        #     flutter_notes_updated.pdf
        #
        # Django's default result:
        #
        #     flutter_notes.pdf            (still exists ❌)
        #     flutter_notes_updated.pdf    (new file ✅)
        #
        # This causes unnecessary storage usage because
        # old files remain on the server forever.
        #
        # Therefore, before saving the updated resource,
        # we first check whether the uploaded file has
        # been replaced. If it has, we delete the old
        # file from the media folder.
        #
        # ==================================================

        # --------------------------------------------------
        # Check whether this resource already exists.
        #
        # If self.pk is None:
        #     This is a NEW resource.
        #
        # If self.pk has a value:
        #     This is an EXISTING resource being edited.
        # --------------------------------------------------

        if self.pk:

            try:

                # ------------------------------------------
                # Retrieve the existing resource from the
                # database before any changes are saved.
                # ------------------------------------------

                old_resource = Resource.objects.get(pk=self.pk)

                # ------------------------------------------
                # Store references to:
                #
                # old_file -> currently stored file
                # new_file -> newly uploaded file
                # ------------------------------------------

                old_file = old_resource.file
                new_file = self.file

                # ------------------------------------------
                # Delete the previous file only if:
                #
                # 1. An old file exists.
                # 2. A new file has been uploaded.
                # 3. The filenames are different.
                #
                # If the filenames are identical,
                # nothing has changed and no deletion
                # is required.
                # ------------------------------------------

                if (
                    old_file
                    and new_file
                    and old_file.name != new_file.name
                ):

                    # --------------------------------------
                    # Verify that the file actually exists
                    # on disk before attempting deletion.
                    #
                    # This prevents FileNotFoundError.
                    # --------------------------------------

                    if os.path.isfile(old_file.path):

                        # ----------------------------------
                        # Permanently remove the old file
                        # from the media directory.
                        # ----------------------------------

                        os.remove(old_file.path)

            # ----------------------------------------------
            # Safety check.
            #
            # In rare situations the resource may not exist
            # in the database anymore. Ignore the exception
            # and continue saving normally.
            # ----------------------------------------------

            except Resource.DoesNotExist:
                pass

        # --------------------------------------------------
        # Save the updated resource (or new resource)
        # using Django's default save() method.
        # --------------------------------------------------

        super().save(*args, **kwargs)



# ============================================================
# RECENT SEARCH
# ============================================================
#
# Stores the latest searches performed by each user.
#
# Example:
#
# User
# -----
# Panchami
#
# Searches
# --------
# Flutter
# Django
# Resume
#
# Only the latest five searches are retained.
#
# ============================================================

class RecentSearch(models.Model):

    # ---------------------------------------
    # User who performed the search
    # ---------------------------------------

    user = models.ForeignKey(

        settings.AUTH_USER_MODEL,

        on_delete=models.CASCADE,

        related_name="recent_searches",

    )

    # ---------------------------------------
    # Search Query
    # ---------------------------------------

    query = models.CharField(

        max_length=255,

    )

    # ---------------------------------------
    # Timestamp
    # ---------------------------------------

    searched_at = models.DateTimeField(

        auto_now=True,

    )

    class Meta:

        ordering = ["-searched_at"]

        verbose_name = "Recent Search"

        verbose_name_plural = "Recent Searches"

    def __str__(self):

        return f"{self.user} - {self.query}"