"""
AI Processor

Coordinates the complete AI pipeline.

Responsibilities
----------------
1. Extract text from a document.
2. Generate an AI summary and keywords.
3. Retry AI processing automatically if it fails.
4. Save AI-generated content.
5. Update AI processing status.
"""
# ==========================================================
# Resource Manager IMPORTS
# ==========================================================
import time

from services.ai.ai_service import analyze_document
from services.document.text_extractor import extract_text
from apps.resource_manager.models import Resource



def process_resource_by_id(resource_id):
    """
    Load a fresh Resource instance from the database and
    process it.

    This is used by background threads so that each thread
    works with its own database object.
    """

    try:

        resource = Resource.objects.get(pk=resource_id)

    except Resource.DoesNotExist:

        return False

    return process_resource(resource)

# ==========================================================
# AI Retry Configuration
# ==========================================================

# Maximum number of AI attempts.
MAX_RETRIES = 4

# Delay (seconds) before each retry.
RETRY_DELAYS = [2, 5, 10, 20]


def process_resource(resource):
    """
    Process a resource using AI.

    Parameters
    ----------
    resource : Resource
        Resource model instance.

    Returns
    -------
    bool
        True if processing succeeds.
        False otherwise.
    """

    # ------------------------------------------------------
    # Skip resources that do not contain uploaded files.
    # External links, YouTube videos, etc. are ignored.
    # ------------------------------------------------------

    if not resource.file:
        return False

    # ------------------------------------------------------
    # Mark AI processing as started.
    # ------------------------------------------------------

    resource.ai_status = "PROCESSING"
    resource.retry_count = 0
    resource.last_error = ""

    resource.save(
        update_fields=[
            "ai_status",
            "retry_count",
            "last_error",
        ]
    )

    # ------------------------------------------------------
    # Extract text from the uploaded document.
    #
    # This is done only once because extracting text from a
    # PDF/DOCX/PPT is deterministic and doesn't need retries.
    # ------------------------------------------------------

    try:

        text = extract_text(resource.file.path)

        # Nothing meaningful could be extracted.
        if not text.strip():

            raise ValueError("Document contains no readable text.")

    except Exception as e:

        resource.ai_status = "FAILED"
        resource.retry_count = 1
        resource.last_error = str(e)

        resource.save(
            update_fields=[
                "ai_status",
                "retry_count",
                "last_error",
            ]
        )

        return False

    # ======================================================
    # Retry AI Processing
    # ======================================================

    for attempt in range(MAX_RETRIES):

        try:

            # Generate summary and keywords.
            ai_result = analyze_document(text)

            resource.summary = ai_result["summary"]
            resource.keywords = ai_result["keywords"]

            resource.ai_status = "COMPLETED"
            resource.retry_count = 0
            resource.last_error = ""

            resource.save(
                update_fields=[
                    "summary",
                    "keywords",
                    "ai_status",
                    "retry_count",
                    "last_error",
                ]
            )

            return True

        except Exception as e:

            resource.retry_count = attempt + 1
            resource.last_error = str(e)

            # Final attempt failed.
            if attempt == MAX_RETRIES - 1:

                resource.ai_status = "FAILED"

                resource.save(
                    update_fields=[
                        "ai_status",
                        "retry_count",
                        "last_error",
                    ]
                )

                return False

            # Save retry progress.
            resource.save(
                update_fields=[
                    "retry_count",
                    "last_error",
                ]
            )

            # Wait before retrying.
            time.sleep(RETRY_DELAYS[attempt])

    return False

