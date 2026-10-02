from pathlib import Path
from datetime import datetime, timedelta

from django.conf import settings


def delete_old_previews(hours=0.5):
    """
    Delete cached preview PDFs older than the
    specified number of hours.
    """

    preview_directory = (
        Path(settings.MEDIA_ROOT)
        / "temp"
    )

    if not preview_directory.exists():
        return

    cutoff_time = datetime.now() - timedelta(hours=hours)

    for preview_pdf in preview_directory.glob("*.pdf"):

        modified_time = datetime.fromtimestamp(
            preview_pdf.stat().st_mtime
        )

        if modified_time < cutoff_time:

            preview_pdf.unlink()