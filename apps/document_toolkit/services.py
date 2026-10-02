"""
services.py

Core document-processing operations for the Document Toolkit.

All functions take real file paths in and return a Path to the
generated output file. No Django request/model objects are
touched here on purpose, so these functions stay easy to test
and reuse (e.g. from a management command later).

Dependencies used (already installed for the rest of the app):
- PyMuPDF (fitz)  -> create, merge, split, rotate, watermark,
                      compress, page numbers
- Pillow          -> images to PDF
- LibreOffice     -> office document conversion, both
                      DOCX/PPTX -> PDF and PDF -> DOCX
"""

import subprocess
import zipfile
import io
from pathlib import Path

import fitz  # PyMuPDF
from django.conf import settings
from PIL import Image

from apps.resource_manager.services.converter import convert_to_pdf as _office_to_pdf


# ============================================================
# CREATE PDF (FROM TEXT)
# ============================================================

def create_pdf_from_text(title, body_text, output_path):
    """
    Build a simple, cleanly formatted PDF from plain text --
    handy for turning quick notes into a shareable document.

    Text is manually word-wrapped and paginated (rather than
    relying on PyMuPDF's insert_textbox, which silently drops
    any text that doesn't fit in a single box instead of
    flowing onto a new page).

    Parameters
    ----------
    title : str
        Optional heading printed at the top of the first page.
    body_text : str
        The note content. Paragraphs are separated by blank lines.
    output_path : str | Path

    Returns
    -------
    Path
    """

    if not body_text or not body_text.strip():
        raise ValueError("Add some text before creating the PDF.")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    page_width, page_height = fitz.paper_size("a4")
    margin = 54  # 0.75"
    content_width = page_width - (margin * 2)
    bottom_limit = page_height - margin

    fontname = "helv"
    body_fontsize = 11.5
    line_height = body_fontsize * 1.45
    paragraph_gap = line_height * 0.6

    doc = fitz.open()
    page = doc.new_page(width=page_width, height=page_height)
    cursor_y = margin

    # -----------------------------------------------------
    # TITLE (first page only)
    # -----------------------------------------------------

    if title and title.strip():
        title_fontsize = 20
        page.insert_text(
            (margin, cursor_y + title_fontsize),
            title.strip(),
            fontsize=title_fontsize,
            fontname=fontname,
            color=(0.11, 0.12, 0.2),
        )
        cursor_y += title_fontsize + 26

    def new_page():
        nonlocal page, cursor_y
        page = doc.new_page(width=page_width, height=page_height)
        cursor_y = margin

    def wrap_line(text):
        """Break a single paragraph's text into lines that fit content_width."""
        words = text.split(" ")
        lines = []
        current = ""

        for word in words:
            candidate = f"{current} {word}".strip()
            if fitz.get_text_length(candidate, fontname=fontname, fontsize=body_fontsize) <= content_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                # Word itself is wider than the page (rare) -- place it anyway.
                current = word

        if current:
            lines.append(current)

        return lines or [""]

    # -----------------------------------------------------
    # BODY -- paragraph by paragraph, line by line,
    # creating new pages as content overflows.
    # -----------------------------------------------------

    paragraphs = body_text.strip().split("\n\n")

    for paragraph_index, paragraph in enumerate(paragraphs):

        for line in wrap_line(paragraph.replace("\n", " ").strip()):

            if cursor_y + line_height > bottom_limit:
                new_page()

            page.insert_text(
                (margin, cursor_y + body_fontsize),
                line,
                fontsize=body_fontsize,
                fontname=fontname,
                color=(0.12, 0.13, 0.2),
            )

            cursor_y += line_height

        if paragraph_index < len(paragraphs) - 1:
            cursor_y += paragraph_gap

    doc.save(str(output_path))
    doc.close()

    return output_path


# ============================================================
# MERGE PDFs
# ============================================================

_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif")


def merge_pdfs(input_paths, output_path):
    """
    Merge multiple files into a single PDF, in the order given.
    Accepts a mix of PDFs and images (JPG/PNG/WEBP/BMP/TIFF) --
    each image is placed on its own centered A4 page, matching
    the position it was given in input_paths.

    Parameters
    ----------
    input_paths : list[str | Path]
        Paths of the PDFs/images to merge, in the desired order.

    output_path : str | Path
        Where the merged PDF should be written.

    Returns
    -------
    Path
    """

    if len(input_paths) < 2:
        raise ValueError("Select at least two files to merge.")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # A4 size in points
    page_width, page_height = 595, 842

    merged = fitz.open()

    try:
        for path in input_paths:

            path = Path(path)
            suffix = path.suffix.lower()

            # -------------------------------------------
            # PDF -- insert as-is
            # -------------------------------------------
            if suffix == ".pdf":
                with fitz.open(str(path)) as part:
                    merged.insert_pdf(part)

            # -------------------------------------------
            # IMAGE -- center on its own A4 page
            # -------------------------------------------
            elif suffix in _IMAGE_EXTENSIONS:

                with fitz.open(str(path)) as image_doc:

                    if image_doc.page_count == 0:
                        raise ValueError(f"Unable to read image: {path.name}")

                    image_rect = image_doc[0].rect
                    image_width, image_height = image_rect.width, image_rect.height

                    scale = min(page_width / image_width, page_height / image_height)
                    display_width = image_width * scale
                    display_height = image_height * scale

                    x = (page_width - display_width) / 2
                    y = (page_height - display_height) / 2

                    placement_rect = fitz.Rect(x, y, x + display_width, y + display_height)

                    image_page_doc = fitz.open()
                    page = image_page_doc.new_page(width=page_width, height=page_height)
                    page.insert_image(placement_rect, filename=str(path))

                    merged.insert_pdf(image_page_doc)
                    image_page_doc.close()

            else:
                raise ValueError(f"{path.name} is not a supported file type (PDF or image only).")

        merged.save(str(output_path))

    finally:
        merged.close()

    return output_path


# ============================================================
# SPLIT / EXTRACT PAGES
# ============================================================

def split_pdf(input_path, start_page, end_page, output_path):
    """
    Extract a page range (inclusive, 1-indexed, as shown to
    the user) from a PDF into a new PDF.

    Parameters
    ----------
    input_path : str | Path
    start_page : int
        First page to keep (1-indexed).
    end_page : int
        Last page to keep (1-indexed, inclusive).
    output_path : str | Path

    Returns
    -------
    Path
    """

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with fitz.open(str(input_path)) as source:

        page_count = source.page_count

        if start_page < 1 or end_page < 1:
            raise ValueError("Page numbers must be 1 or greater.")

        if start_page > page_count or end_page > page_count:
            raise ValueError(
                f"This PDF only has {page_count} page(s)."
            )

        if start_page > end_page:
            raise ValueError("Start page cannot be after end page.")

        extracted = fitz.open()

        try:
            # PyMuPDF page numbers are 0-indexed internally.
            extracted.insert_pdf(
                source,
                from_page=start_page - 1,
                to_page=end_page - 1,
            )

            extracted.save(str(output_path))

        finally:
            extracted.close()

    return output_path


def split_pdf_every_page(input_path, output_zip_path):
    """
    Split a PDF into one single-page PDF per page, packaged
    into a downloadable ZIP.

    Parameters
    ----------
    input_path : str | Path
    output_zip_path : str | Path

    Returns
    -------
    Path
        Path to the generated ZIP file.
    """

    output_zip_path = Path(output_zip_path)
    output_zip_path.parent.mkdir(parents=True, exist_ok=True)

    stem = Path(input_path).stem

    with fitz.open(str(input_path)) as source:

        page_count = source.page_count

        if page_count < 2:
            raise ValueError("This PDF only has one page -- nothing to split.")

        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:

            for index in range(page_count):

                single = fitz.open()
                single.insert_pdf(source, from_page=index, to_page=index)

                page_bytes = single.tobytes()
                single.close()

                zf.writestr(f"{stem}_page_{index + 1}.pdf", page_bytes)

    return output_zip_path


# ============================================================
# ROTATE PDF
# ============================================================

def rotate_pdf(input_path, angle, output_path):
    """
    Rotate every page of a PDF by the given angle.

    Parameters
    ----------
    input_path : str | Path
    angle : int
        One of 90, 180, 270 (clockwise).
    output_path : str | Path

    Returns
    -------
    Path
    """

    if angle not in (90, 180, 270):
        raise ValueError("Rotation angle must be 90, 180 or 270 degrees.")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with fitz.open(str(input_path)) as doc:

        for page in doc:
            new_rotation = (page.rotation + angle) % 360
            page.set_rotation(new_rotation)

        doc.save(str(output_path))

    return output_path


# ============================================================
# WATERMARK PDF
# ============================================================

def watermark_pdf(input_path, text, output_path):
    """
    Stamp a diagonal, semi-transparent text watermark across
    every page of a PDF.

    Parameters
    ----------
    input_path : str | Path
    text : str
        Watermark text, e.g. "CONFIDENTIAL" or a student's name.
    output_path : str | Path

    Returns
    -------
    Path
    """

    if not text or not text.strip():
        raise ValueError("Watermark text cannot be empty.")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with fitz.open(str(input_path)) as doc:

        for page in doc:

            rect = page.rect
            center = fitz.Point(rect.width / 2, rect.height / 2)
            rotation_matrix = fitz.Matrix(45)

            page.insert_textbox(
                rect,
                text.strip(),
                fontsize=42,
                fontname="helv",
                color=(0.55, 0.55, 0.6),
                fill_opacity=0.28,
                morph=(center, rotation_matrix),
                align=1,  # centered
            )

        doc.save(str(output_path))

    return output_path


# ============================================================
# ADD PAGE NUMBERS
# ============================================================

def add_page_numbers(input_path, output_path, vertical_position="bottom",
                      alignment="center", number_format="page_of",
                      start_at=1, font_size=10):
    """
    Stamp page numbers onto every page of a PDF.

    Parameters
    ----------
    input_path : str | Path
    output_path : str | Path
    vertical_position : str
        "bottom" or "top".
    alignment : str
        "left", "center", or "right".
    number_format : str
        "plain" -> "1", "page" -> "Page 1", "page_of" -> "Page 1 of 10".
    start_at : int
        The number to print on the first page.
    font_size : int

    Returns
    -------
    Path
    """

    if vertical_position not in ("bottom", "top"):
        raise ValueError(f"Unsupported vertical position: {vertical_position}")

    if alignment not in ("left", "center", "right"):
        raise ValueError(f"Unsupported alignment: {alignment}")

    format_templates = {
        "plain": "{n}",
        "page": "Page {n}",
        "page_of": "Page {n} of {total}",
    }
    fmt = format_templates.get(number_format, "Page {n} of {total}")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with fitz.open(str(input_path)) as doc:

        total = doc.page_count
        margin = 26
        box_height = font_size + 14

        for index, page in enumerate(doc):

            number = start_at + index
            label = fmt.format(n=number, total=total)

            rect = page.rect

            if vertical_position == "bottom":
                y0, y1 = rect.height - margin - box_height, rect.height - margin
            else:
                y0, y1 = margin, margin + box_height

            if alignment == "center":
                x0, x1 = rect.width * 0.25, rect.width * 0.75
                align = 1
            elif alignment == "right":
                x0, x1 = rect.width * 0.5, rect.width - margin
                align = 2
            else:  # left
                x0, x1 = margin, rect.width * 0.5
                align = 0

            box = fitz.Rect(x0, y0, x1, y1)

            page.insert_textbox(
                box, label,
                fontsize=font_size,
                fontname="helv",
                color=(0.35, 0.35, 0.4),
                align=align,
            )

        doc.save(str(output_path))

    return output_path

# ============================================================
# COMPRESS PDF
# ============================================================

def compress_pdf(input_path, output_path, image_quality="medium"):
    """
    Reduce a PDF's file size.

    Strategy:
    1. Downsample every embedded image to a sensible max
       resolution for the chosen quality level, then re-encode
       it -- JPEG for opaque images, PNG for images that need to
       keep transparency.
    2. Structural cleanup -- strip unused/duplicate objects and
       deflate content streams.

    Downsampling the pixel dimensions is what actually drives
    file size down. A photo scanned at 300+ DPI is still huge
    at "quality 40" if you only lower the JPEG quality and leave
    every pixel in place -- so the resolution cap below matters
    at least as much as the quality number.

    Parameters
    ----------
    input_path : str | Path
    output_path : str | Path
    image_quality : str
        "low", "medium", or "high". Controls both the JPEG
        quality used and how aggressively images are downsampled.

    Returns
    -------
    Path
    """

    # jpeg_quality: JPEG compression level for opaque images.
    # max_dimension: images with a longer side above this (in
    # pixels) are downsampled to it before re-encoding. Smaller
    # images are left at their native size -- we only ever shrink,
    # never upscale.
    presets = {
        "low":    {"jpeg_quality": 35, "max_dimension": 1000},
        "medium": {"jpeg_quality": 55, "max_dimension": 1500},
        "high":   {"jpeg_quality": 75, "max_dimension": 2000},
    }

    preset = presets.get(image_quality, presets["medium"])
    jpeg_quality = preset["jpeg_quality"]
    max_dimension = preset["max_dimension"]

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with fitz.open(str(input_path)) as doc:

        for page in doc:

            for image_info in page.get_images(full=True):

                xref = image_info[0]

                try:
                    pixmap = fitz.Pixmap(doc, xref)

                    if pixmap.colorspace is None:
                        # Stencil masks and other colorspace-less
                        # images aren't safe to touch.
                        continue

                    # Grayscale (n=1) and RGB (n=3) can be handled
                    # directly. Anything else (CMYK, indexed, etc.)
                    # gets converted to RGB first so it can go
                    # through the same path -- this also fixes
                    # images that were previously skipped entirely.
                    if pixmap.colorspace.n not in (1, 3):
                        pixmap = fitz.Pixmap(fitz.csRGB, pixmap)

                    original_image = doc.extract_image(xref)

                    if not original_image:
                        continue

                    original_bytes = original_image["image"]

                    # Pillow decodes the pixmap (any soft mask/alpha
                    # PyMuPDF already merged in comes through as an
                    # RGBA/LA image, so transparency is preserved
                    # automatically -- no special-casing needed).
                    pil_image = Image.open(io.BytesIO(pixmap.tobytes("png")))

                    # ---- Downsample -- the main lever for size ----
                    longest_side = max(pil_image.width, pil_image.height)

                    if longest_side > max_dimension:
                        scale = max_dimension / longest_side
                        new_size = (
                            max(1, round(pil_image.width * scale)),
                            max(1, round(pil_image.height * scale)),
                        )
                        pil_image = pil_image.resize(new_size, Image.LANCZOS)

                    has_alpha = pil_image.mode in ("RGBA", "LA", "PA")

                    buffer = io.BytesIO()

                    if has_alpha:
                        # JPEG can't hold transparency -- keep PNG,
                        # but it still benefits from the resize above.
                        pil_image.save(buffer, format="PNG", optimize=True)
                    else:
                        if pil_image.mode not in ("RGB", "L"):
                            pil_image = pil_image.convert("RGB")

                        pil_image.save(
                            buffer,
                            format="JPEG",
                            quality=jpeg_quality,
                            optimize=True,
                        )

                    new_bytes = buffer.getvalue()

                    # Only replace the image if compression actually
                    # makes it smaller.
                    if len(new_bytes) >= len(original_bytes):
                        continue

                    page.replace_image(
                        xref,
                        stream=new_bytes,
                    )

                except Exception:
                    # Leave problematic images untouched.
                    continue

        doc.save(
            str(output_path),
            garbage=4,
            deflate=True,
            deflate_images=True,
            deflate_fonts=True,
            clean=True,
        )

    return output_path


# ============================================================
# IMAGES TO PDF
# ============================================================

def images_to_pdf(image_paths, output_path):
    """
    Combine one or more images (JPG/PNG) into a single PDF,
    one image per page, in the given order.

    Parameters
    ----------
    image_paths : list[str | Path]
    output_path : str | Path

    Returns
    -------
    Path
    """

    if not image_paths:
        raise ValueError("Select at least one image.")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    images = []

    for path in image_paths:
        img = Image.open(path)

        # PDFs need RGB (no alpha channel).
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")

        images.append(img)

    first, rest = images[0], images[1:]

    first.save(
        str(output_path),
        save_all=True,
        append_images=rest,
    )

    return output_path


# ============================================================
# CONVERT OFFICE DOCUMENT TO PDF
# ============================================================
#
# Thin wrapper around the LibreOffice-based converter already
# used by resource_manager, so both apps stay in sync and we
# don't maintain two conversion code paths.
# ============================================================

def convert_office_to_pdf(input_path, output_directory):
    """
    Convert a DOC/DOCX/PPT/PPTX file to PDF using LibreOffice.

    Returns
    -------
    Path
        Path to the generated PDF.
    """

    return _office_to_pdf(input_path, output_directory)


# ============================================================
# CONVERT PDF TO DOCX
# ============================================================

def convert_pdf_to_docx(input_path, output_directory):
    """
    Convert a PDF into an editable Word document using
    LibreOffice's Writer PDF-import filter.

    Note: layout fidelity depends on how the PDF was produced.
    Text-based PDFs convert well; scanned/image-only PDFs will
    come back mostly empty since this isn't OCR.

    Parameters
    ----------
    input_path : str | Path
    output_directory : str | Path

    Returns
    -------
    Path
        Path to the generated DOCX.
    """

    input_path = Path(input_path)
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)

    output_docx = output_directory / f"{input_path.stem}.docx"

    command = [
        settings.LIBREOFFICE_PATH,
        "--headless",
        "--infilter=writer_pdf_import",
        "--convert-to", "docx:MS Word 2007 XML",
        "--outdir", str(output_directory),
        str(input_path),
    ]

    try:
        subprocess.run(command, capture_output=True, text=True, check=True)

    except subprocess.CalledProcessError as error:
        raise Exception(f"PDF to DOCX conversion failed:\n{error.stderr}")

    if not output_docx.exists():
        raise FileNotFoundError(f"Generated DOCX not found:\n{output_docx}")

    return output_docx
