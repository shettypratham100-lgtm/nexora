from django.db import models
from django.conf import settings
import os


# ============================================================
# TOOL JOB
# ============================================================
#
# Every time a user runs a Document Toolkit tool (merge,
# split, convert, etc.) we keep a lightweight history record
# pointing at the generated output file, so the user can come
# back and re-download it later without redoing the work.
# ============================================================

class ToolJob(models.Model):

    class ToolType(models.TextChoices):

        MERGE = "MERGE", "Merge PDFs"
        SPLIT = "SPLIT", "Split PDF"
        CONVERT = "CONVERT", "Convert to PDF"
        IMAGE_TO_PDF = "IMAGE_TO_PDF", "Images to PDF"
        WATERMARK = "WATERMARK", "Watermark PDF"
        ROTATE = "ROTATE", "Rotate PDF"

    class Status(models.TextChoices):

        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="toolkit_jobs",
    )

    tool_type = models.CharField(
        max_length=20,
        choices=ToolType.choices,
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.SUCCESS,
    )

    # Human readable summary shown in history.
    # e.g. "3 files merged" / "Pages 2-5 extracted"
    summary = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    output_file = models.FileField(
        upload_to="toolkit_outputs/",
        blank=True,
        null=True,
    )

    error_message = models.TextField(
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:

        ordering = ["-created_at"]
        verbose_name = "Tool Job"
        verbose_name_plural = "Tool Jobs"

    def __str__(self):
        return f"{self.user.username} - {self.get_tool_type_display()} ({self.created_at:%d %b %Y})"

    @property
    def output_filename(self):
        if self.output_file:
            return os.path.basename(self.output_file.name)
        return ""

    def delete(self, *args, **kwargs):

        # Clean up the file on disk when the history record
        # is removed, same pattern used by Resource.
        if self.output_file and os.path.isfile(self.output_file.path):
            os.remove(self.output_file.path)

        super().delete(*args, **kwargs)
