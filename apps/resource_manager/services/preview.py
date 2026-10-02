"""
preview.py

This module is responsible for providing
a PDF preview for every supported resource.

If the uploaded file is already a PDF,
the original file is returned.

Otherwise, the document is converted into
a temporary PDF preview using LibreOffice.
"""

from pathlib import Path

import hashlib

from django.conf import settings

from .converter import convert_to_pdf

import mimetypes

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".webp",
}

def get_preview_pdf(resource):
    """
    Returns a PDF that can be displayed
    inside PDF.js.

    Parameters
    ----------
    resource : Resource
        Uploaded resource.

    Returns
    -------
    Path
        Path of the PDF to display.
    """

    # ---------------------------------------------------------
    # Path of the uploaded file.
    #
    # Example:
    #
    # media/resources/java.docx
    # ---------------------------------------------------------
    original_file = Path(resource.file.path)

    # ---------------------------------------------------------
    # Extract file extension.
    #
    # Examples:
    #
    # java.docx
    #      ↓
    # .docx
    # ---------------------------------------------------------
    extension = original_file.suffix.lower()

    # ---------------------------------------------------------
    # If the uploaded file is already a PDF,
    # no conversion is needed.
    #
    # Simply return the original file.
    # ---------------------------------------------------------
    if extension == ".pdf":

        return original_file

    # Images don't need conversion either.
    if extension in IMAGE_EXTENSIONS:
        return original_file

    # ---------------------------------------------------------
    # Create the path where the generated preview PDF
    # will be stored.
    #
    # Example:
    #
    # media/
    #     temp/
    #         15.pdf
    #
    # The resource ID is used as the filename to ensure
    # every preview is unique.
    # ---------------------------------------------------------

    preview_directory = (
        Path(settings.MEDIA_ROOT)
        / "temp"
    )

    # ---------------------------------------------------------
    # Generate a SHA-256 hash from the uploaded file.
    #
    # Instead of using the resource ID, we hash the actual
    # file contents.
    #
    # Advantages:
    #
    # • Same document -> Same preview filename
    #
    # • Different document -> Different preview filename
    #
    # • If the file changes, the hash changes automatically,
    #   so a new preview will be generated.
    #
    # This creates a reliable cache without storing preview
    # information in the database.
    # ---------------------------------------------------------

    sha256 = hashlib.sha256()

    with open(original_file, "rb") as file:

        # Read the file in chunks instead of loading the
        # entire file into memory.
        #
        # This is more memory-efficient, especially for
        # large documents.
        for chunk in iter(lambda: file.read(8192), b""):

            sha256.update(chunk)

    # ---------------------------------------------------------
    # Convert the SHA-256 hash into a hexadecimal string.
    #
    # Example:
    #
    # f82d91ab73...
    #
    # This becomes the preview filename.
    # ---------------------------------------------------------

    preview_pdf = (

        preview_directory

        / f"{sha256.hexdigest()}.pdf"

    )

    # ---------------------------------------------------------
    # Check whether the preview PDF has already been
    # generated.
    #
    # If it exists, we don't need to convert the document
    # again.
    #
    # This makes repeated views much faster.
    # ---------------------------------------------------------

    if preview_pdf.exists():

        return preview_pdf

    # ---------------------------------------------------------
    # No cached preview was found.
    #
    # Convert the uploaded Office document into a PDF.
    #
    # The converter returns the path of the newly
    # generated PDF.
    # ---------------------------------------------------------

    generated_pdf = convert_to_pdf(
        input_file_path=original_file,
        output_directory=preview_directory
    )

    # ---------------------------------------------------------
    # Rename the generated PDF to use the resource ID.
    #
    # Example:
    #
    # Java Notes.pdf
    #
    # becomes
    #
    # 15.pdf
    #
    # This guarantees every preview filename
    # is unique.
    # ---------------------------------------------------------

    generated_pdf.replace(preview_pdf)

    # ---------------------------------------------------------
    # Return the cached preview PDF.
    #
    # The calling view can now display this PDF
    # using PDF.js.
    # ---------------------------------------------------------

    return preview_pdf