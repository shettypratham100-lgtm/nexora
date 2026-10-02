import os
import tempfile
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files import File
from django.shortcuts import render, redirect, get_object_or_404

from . import services
from .forms import (
    CreatePdfForm,
    MergePdfForm,
    SplitPdfForm,
    CompressPdfForm,
    PageNumbersForm,
    WatermarkPdfForm,
    RotatePdfForm,
    SingleFileForm,
)
from .models import ToolJob


# ============================================================
# TOOL CATALOG
#
# Drives the home page grid. Each tool page is still its own
# view/template below -- this dict is purely for display.
# ============================================================

TOOL_CATALOG = [
    {
        "slug": "create-pdf",
        "title": "Create PDF",
        "description": "Turn typed or pasted notes into a clean PDF document.",
        "icon": "bi-file-earmark-plus",
        "accent": "violet",
        "url_name": "document_toolkit:create_pdf",
    },
    {
        "slug": "merge-pdf",
        "title": "Merge PDF",
        "description": "Combine PDFs and images into a single file, in any order.",
        "icon": "bi-union",
        "accent": "teal",
        "url_name": "document_toolkit:merge_pdf",
    },
    {
        "slug": "split-pdf",
        "title": "Split PDF",
        "description": "Extract a page range, or split every page into its own file.",
        "icon": "bi-scissors",
        "accent": "amber",
        "url_name": "document_toolkit:split_pdf",
    },
    {
        "slug": "compress-pdf",
        "title": "Compress PDF",
        "description": "Shrink a PDF's file size by optimizing embedded images.",
        "icon": "bi-file-earmark-zip",
        "accent": "coral",
        "url_name": "document_toolkit:compress_pdf",
    },
    {
        "slug": "page-numbers",
        "title": "Add Page Numbers",
        "description": "Stamp customizable page numbers across every page.",
        "icon": "bi-list-ol",
        "accent": "violet",
        "url_name": "document_toolkit:page_numbers",
    },
    {
        "slug": "watermark-pdf",
        "title": "Watermark PDF",
        "description": "Overlay a text watermark across every page.",
        "icon": "bi-droplet-half",
        "accent": "teal",
        "url_name": "document_toolkit:watermark_pdf",
    },
    {
        "slug": "rotate-pdf",
        "title": "Rotate PDF",
        "description": "Rotate every page 90°, 180°, or 270°.",
        "icon": "bi-arrow-clockwise",
        "accent": "amber",
        "url_name": "document_toolkit:rotate_pdf",
    },
    {
        "slug": "pdf-to-docx",
        "title": "PDF → DOCX",
        "description": "Convert a PDF into an editable Word document.",
        "icon": "bi-file-earmark-word",
        "accent": "coral",
        "url_name": "document_toolkit:pdf_to_docx",
    },
    {
        "slug": "docx-to-pdf",
        "title": "DOCX → PDF",
        "description": "Convert a Word document into a PDF.",
        "icon": "bi-file-earmark-pdf",
        "accent": "violet",
        "url_name": "document_toolkit:docx_to_pdf",
    },
    {
        "slug": "ppt-to-pdf",
        "title": "PPT/PPTX → PDF",
        "description": "Convert a PowerPoint presentation into a PDF.",
        "icon": "bi-file-earmark-slides",
        "accent": "teal",
        "url_name": "document_toolkit:ppt_to_pdf",
    },
    {
        "slug": "image-to-pdf",
        "title": "Image → PDF",
        "description": "Combine one or more images into a single PDF.",
        "icon": "bi-file-earmark-image",
        "accent": "amber",
        "url_name": "document_toolkit:image_to_pdf",
    },
]


# ============================================================
# HELPERS
# ============================================================

def _save_upload_to_temp(uploaded_file):
    """
    Write an in-memory/uploaded file to a real temp path on
    disk, so libraries that expect file paths (PyMuPDF,
    LibreOffice, Pillow) can work with it directly.
    """

    suffix = Path(uploaded_file.name).suffix.lower()

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:

        for chunk in uploaded_file.chunks():
            temp_file.write(chunk)

        return temp_file.name


def _toolkit_temp_dir():
    directory = Path(settings.MEDIA_ROOT) / "toolkit_temp"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _save_job(request, tool_type, output_path, summary):
    """
    Create a ToolJob history record pointing at a generated
    output file, and return it.
    """

    job = ToolJob(
        user=request.user,
        tool_type=tool_type,
        status=ToolJob.Status.SUCCESS,
        summary=summary,
    )

    output_path = Path(output_path)

    with open(output_path, "rb") as f:
        job.output_file.save(output_path.name, File(f), save=True)

    return job



# ------------------------------------------------------------
# RESULT STACK (per tool, per session)
#
# A plain page reload after a conversion always renders the
# exact same "Done!" markup, so running a tool twice in a row
# looked completely identical -- nothing told the user whether
# they were looking at a fresh result or the previous one.
#
# Instead of swapping the single result panel out, we keep a
# short history (newest first) of the jobs run for THIS tool in
# THIS browser session, so results stack up as the user keeps
# converting, and the template can flag the newest one.
# ------------------------------------------------------------

RESULT_STACK_SIZE = 5


def _get_job_stack(request, tool_slug, latest_job=None):
    """
    Returns up to RESULT_STACK_SIZE ToolJob objects (newest
    first) for this tool, scoped to the current session.

    If `latest_job` is given, it's pushed to the front of the
    stack first (deduping if it's already there).
    """

    session_key = f"toolkit_stack::{tool_slug}"
    job_ids = request.session.get(session_key, [])

    if latest_job is not None:
        job_ids = [latest_job.pk] + [pk for pk in job_ids if pk != latest_job.pk]
        job_ids = job_ids[:RESULT_STACK_SIZE]
        request.session[session_key] = job_ids

    if not job_ids:
        return []

    jobs_by_id = ToolJob.objects.in_bulk(job_ids)

    # Preserve newest-first order and silently drop any job
    # that's since been removed from history.
    return [jobs_by_id[pk] for pk in job_ids if pk in jobs_by_id]


def _cleanup(*paths):
    for path in paths:
        try:
            if path and os.path.isfile(path):
                os.remove(path)
        except OSError:
            pass


# ============================================================
# HOME
# ============================================================

@login_required
def toolkit_home(request):

    # Fetch a generous batch (not just the 5 we show by default) --
    # the template shows the 5 most recent and makes the rest
    # reachable by scrolling within a fixed-height list instead of
    # the page growing forever as someone runs more conversions.
    recent_jobs = ToolJob.objects.filter(user=request.user)[:30]

    return render(
        request,
        "document_toolkit/home.html",
        {
            "tools": TOOL_CATALOG,
            "recent_jobs": recent_jobs,
        },
    )


# ============================================================
# CREATE PDF (FROM TEXT)
# ============================================================

@login_required
def create_pdf(request):

    job = None

    if request.method == "POST":

        form = CreatePdfForm(request.POST)

        if form.is_valid():

            output_dir = _toolkit_temp_dir()
            file_stem = form.cleaned_data["title"].strip() or "note"
            output_path = output_dir / f"{file_stem}.pdf"

            try:
                services.create_pdf_from_text(
                    title=form.cleaned_data["title"],
                    body_text=form.cleaned_data["body_text"],
                    output_path=output_path,
                )

                job = _save_job(request, ToolJob.ToolType.CONVERT, output_path, "Created PDF from notes")

            except Exception as error:
                messages.error(request, str(error))

            finally:
                _cleanup(output_path)

    else:
        form = CreatePdfForm()

    job_stack = _get_job_stack(request, "create-pdf", job)

    return render(request, "document_toolkit/create_pdf.html", {
        "form": form,
        "job_stack": job_stack,
        "tool_title": "Create PDF",
        "tool_description": "Turn typed or pasted notes into a clean PDF document.",
        "tool_icon": "bi-file-earmark-plus",
        "tool_accent": "violet",
    })


# ============================================================
# MERGE PDF
# ============================================================

@login_required
def merge_pdf(request):

    job = None

    if request.method == "POST":

        form = MergePdfForm(request.POST)
        uploaded_files = request.FILES.getlist("files")

        if len(uploaded_files) < 2:
            messages.error(request, "Select at least two files to merge.")

        elif form.is_valid():

            temp_paths = [_save_upload_to_temp(f) for f in uploaded_files]
            output_path = _toolkit_temp_dir() / "merged.pdf"

            try:
                services.merge_pdfs(temp_paths, output_path)
                job = _save_job(
                    request, ToolJob.ToolType.MERGE, output_path,
                    f"{len(uploaded_files)} files merged",
                )

            except Exception as error:
                messages.error(request, str(error))

            finally:
                _cleanup(*temp_paths, output_path)

    else:
        form = MergePdfForm()

    job_stack = _get_job_stack(request, "merge-pdf", job)

    return render(request, "document_toolkit/merge_pdf.html", {
        "form": form,
        "job_stack": job_stack,
        "tool_title": "Merge PDF",
        "tool_description": "Combine PDFs and images into a single file, in any order.",
        "tool_icon": "bi-union",
        "tool_accent": "teal",
    })


# ============================================================
# SPLIT PDF
# ============================================================

@login_required
def split_pdf(request):

    job = None

    if request.method == "POST":

        form = SplitPdfForm(request.POST)
        uploaded_file = request.FILES.get("file")

        if not uploaded_file:
            messages.error(request, "Select a PDF file to split.")

        elif form.is_valid():

            temp_path = _save_upload_to_temp(uploaded_file)
            mode = form.cleaned_data["mode"]

            try:
                if mode == "range":

                    start_page = form.cleaned_data["start_page"]
                    end_page = form.cleaned_data["end_page"]
                    output_path = _toolkit_temp_dir() / "extracted.pdf"

                    services.split_pdf(temp_path, start_page, end_page, output_path)

                    job = _save_job(
                        request, ToolJob.ToolType.SPLIT, output_path,
                        f"Pages {start_page}-{end_page} extracted",
                    )

                else:

                    output_path = _toolkit_temp_dir() / "split_pages.zip"

                    services.split_pdf_every_page(temp_path, output_path)

                    job = _save_job(
                        request, ToolJob.ToolType.SPLIT, output_path,
                        "Split into individual pages",
                    )

                _cleanup(output_path)

            except Exception as error:
                messages.error(request, str(error))

            finally:
                _cleanup(temp_path)

    else:
        form = SplitPdfForm(initial={"mode": "range"})

    job_stack = _get_job_stack(request, "split-pdf", job)

    return render(request, "document_toolkit/split_pdf.html", {
        "form": form,
        "job_stack": job_stack,
        "tool_title": "Split PDF",
        "tool_description": "Extract a page range, or split every page into its own file.",
        "tool_icon": "bi-scissors",
        "tool_accent": "amber",
    })


# ============================================================
# COMPRESS PDF
# ============================================================

@login_required
def compress_pdf(request):

    job = None

    if request.method == "POST":

        form = CompressPdfForm(request.POST)
        uploaded_file = request.FILES.get("file")

        if not uploaded_file:
            messages.error(request, "Select a PDF file to compress.")

        elif form.is_valid():

            temp_path = _save_upload_to_temp(uploaded_file)
            output_path = _toolkit_temp_dir() / "compressed.pdf"

            try:
                original_size = os.path.getsize(temp_path)

                services.compress_pdf(
                    temp_path,
                    output_path,
                    image_quality=form.cleaned_data["image_quality"],
                )

                new_size = os.path.getsize(output_path)

                saved_pct = (
                    round((1 - (new_size / original_size)) * 100)
                    if original_size
                    else 0
                )

                job = _save_job(
                    request,
                    ToolJob.ToolType.CONVERT,
                    output_path,
                    f"Compressed -- {saved_pct}% smaller",
                )

            except Exception as error:
                messages.error(request, str(error))

            finally:
                _cleanup(temp_path, output_path)

    else:
        form = CompressPdfForm()

    job_stack = _get_job_stack(request, "compress-pdf", job)

    return render(request, "document_toolkit/compress_pdf.html", {
        "form": form,
        "job_stack": job_stack,
        "tool_title": "Compress PDF",
        "tool_description": "Shrink a PDF's file size by optimizing embedded images.",
        "tool_icon": "bi-file-earmark-zip",
        "tool_accent": "coral",
    })
# ============================================================
# ADD PAGE NUMBERS
# ============================================================

@login_required
def page_numbers(request):

    job = None

    if request.method == "POST":

        form = PageNumbersForm(request.POST)
        uploaded_file = request.FILES.get("file")

        if not uploaded_file:
            messages.error(request, "Select a PDF file.")

        elif form.is_valid():

            temp_path = _save_upload_to_temp(uploaded_file)
            output_path = _toolkit_temp_dir() / "numbered.pdf"

            try:
                services.add_page_numbers(
                    temp_path, output_path,
                    vertical_position=form.cleaned_data["vertical_position"],
                    alignment=form.cleaned_data["alignment"],
                    number_format=form.cleaned_data["number_format"],
                    start_at=form.cleaned_data["start_at"],
                    font_size=form.cleaned_data["font_size"],
                )

                job = _save_job(request, ToolJob.ToolType.CONVERT, output_path, "Page numbers added")

            except Exception as error:
                messages.error(request, str(error))

            finally:
                _cleanup(temp_path, output_path)

    else:
        form = PageNumbersForm()

    job_stack = _get_job_stack(request, "page-numbers", job)

    return render(request, "document_toolkit/page_numbers.html", {
        "form": form,
        "job_stack": job_stack,
        "tool_title": "Add Page Numbers",
        "tool_description": "Stamp customizable page numbers across every page.",
        "tool_icon": "bi-list-ol",
        "tool_accent": "violet",
    })


# ============================================================
# WATERMARK PDF
# ============================================================

@login_required
def watermark_pdf(request):

    job = None

    if request.method == "POST":

        form = WatermarkPdfForm(request.POST)
        uploaded_file = request.FILES.get("file")

        if not uploaded_file:
            messages.error(request, "Select a PDF file.")

        elif form.is_valid():

            temp_path = _save_upload_to_temp(uploaded_file)
            output_path = _toolkit_temp_dir() / "watermarked.pdf"

            try:
                services.watermark_pdf(
                    temp_path, form.cleaned_data["watermark_text"], output_path,
                )

                job = _save_job(request, ToolJob.ToolType.WATERMARK, output_path, "Watermark applied")

            except Exception as error:
                messages.error(request, str(error))

            finally:
                _cleanup(temp_path, output_path)

    else:
        form = WatermarkPdfForm()

    job_stack = _get_job_stack(request, "watermark-pdf", job)

    return render(request, "document_toolkit/watermark_pdf.html", {
        "form": form,
        "job_stack": job_stack,
        "tool_title": "Watermark PDF",
        "tool_description": "Overlay a text watermark across every page.",
        "tool_icon": "bi-droplet-half",
        "tool_accent": "teal",
    })


# ============================================================
# ROTATE PDF
# ============================================================

@login_required
def rotate_pdf(request):

    job = None

    if request.method == "POST":

        form = RotatePdfForm(request.POST)
        uploaded_file = request.FILES.get("file")

        if not uploaded_file:
            messages.error(request, "Select a PDF file.")

        elif form.is_valid():

            temp_path = _save_upload_to_temp(uploaded_file)
            output_path = _toolkit_temp_dir() / "rotated.pdf"

            try:
                angle = form.cleaned_data["angle"]

                services.rotate_pdf(temp_path, angle, output_path)

                job = _save_job(
                    request, ToolJob.ToolType.ROTATE, output_path,
                    f"Rotated {angle}°",
                )

            except Exception as error:
                messages.error(request, str(error))

            finally:
                _cleanup(temp_path, output_path)

    else:
        form = RotatePdfForm(initial={"angle": 90})

    job_stack = _get_job_stack(request, "rotate-pdf", job)

    return render(request, "document_toolkit/rotate_pdf.html", {
        "form": form,
        "job_stack": job_stack,
        "tool_title": "Rotate PDF",
        "tool_description": "Rotate every page 90°, 180°, or 270°.",
        "tool_icon": "bi-arrow-clockwise",
        "tool_accent": "amber",
    })


# ============================================================
# PDF -> DOCX
# ============================================================

@login_required
def pdf_to_docx(request):

    job = None

    if request.method == "POST":

        form = SingleFileForm(request.POST)
        uploaded_file = request.FILES.get("file")

        if not uploaded_file:
            messages.error(request, "Select a PDF file.")

        elif form.is_valid():

            temp_path = _save_upload_to_temp(uploaded_file)
            output_dir = _toolkit_temp_dir()

            try:
                output_path = services.convert_pdf_to_docx(temp_path, output_dir)
                job = _save_job(request, ToolJob.ToolType.CONVERT, output_path, "PDF converted to DOCX")

            except Exception as error:
                messages.error(request, str(error))

            finally:
                _cleanup(temp_path, locals().get("output_path"))

    else:
        form = SingleFileForm()

    job_stack = _get_job_stack(request, "pdf-to-docx", job)

    return render(request, "document_toolkit/pdf_to_docx.html", {
        "form": form,
        "job_stack": job_stack,
        "tool_title": "PDF to DOCX",
        "tool_description": "Convert a PDF into an editable Word document.",
        "tool_icon": "bi-file-earmark-word",
        "tool_accent": "coral",
    })


# ============================================================
# DOCX -> PDF
# ============================================================

@login_required
def docx_to_pdf(request):

    job = None

    if request.method == "POST":

        form = SingleFileForm(request.POST)
        uploaded_file = request.FILES.get("file")

        if not uploaded_file:
            messages.error(request, "Select a DOCX file.")

        elif form.is_valid():

            temp_path = _save_upload_to_temp(uploaded_file)
            output_dir = _toolkit_temp_dir()

            try:
                output_path = services.convert_office_to_pdf(temp_path, output_dir)
                job = _save_job(request, ToolJob.ToolType.CONVERT, output_path, "DOCX converted to PDF")

            except Exception as error:
                messages.error(request, str(error))

            finally:
                _cleanup(temp_path, locals().get("output_path"))

    else:
        form = SingleFileForm()

    job_stack = _get_job_stack(request, "docx-to-pdf", job)

    return render(request, "document_toolkit/docx_to_pdf.html", {
        "form": form,
        "job_stack": job_stack,
        "tool_title": "DOCX to PDF",
        "tool_description": "Convert a Word document into a PDF.",
        "tool_icon": "bi-file-earmark-pdf",
        "tool_accent": "violet",
    })


# ============================================================
# PPT/PPTX -> PDF
# ============================================================

@login_required
def ppt_to_pdf(request):

    job = None

    if request.method == "POST":

        form = SingleFileForm(request.POST)
        uploaded_file = request.FILES.get("file")

        if not uploaded_file:
            messages.error(request, "Select a PPT/PPTX file.")

        elif form.is_valid():

            temp_path = _save_upload_to_temp(uploaded_file)
            output_dir = _toolkit_temp_dir()

            try:
                output_path = services.convert_office_to_pdf(temp_path, output_dir)
                job = _save_job(request, ToolJob.ToolType.CONVERT, output_path, "Presentation converted to PDF")

            except Exception as error:
                messages.error(request, str(error))

            finally:
                _cleanup(temp_path, locals().get("output_path"))

    else:
        form = SingleFileForm()

    job_stack = _get_job_stack(request, "ppt-to-pdf", job)

    return render(request, "document_toolkit/ppt_to_pdf.html", {
        "form": form,
        "job_stack": job_stack,
        "tool_title": "PPT/PPTX to PDF",
        "tool_description": "Convert a PowerPoint presentation into a PDF.",
        "tool_icon": "bi-file-earmark-slides",
        "tool_accent": "teal",
    })


# ============================================================
# IMAGE(S) -> PDF
# ============================================================

@login_required
def image_to_pdf(request):

    job = None

    if request.method == "POST":

        form = SingleFileForm(request.POST)
        uploaded_files = request.FILES.getlist("files")

        if not uploaded_files:
            messages.error(request, "Select at least one image.")

        elif form.is_valid():

            temp_paths = [_save_upload_to_temp(f) for f in uploaded_files]
            output_path = _toolkit_temp_dir() / "images.pdf"

            try:
                services.images_to_pdf(temp_paths, output_path)

                job = _save_job(
                    request, ToolJob.ToolType.IMAGE_TO_PDF, output_path,
                    f"{len(uploaded_files)} image(s) combined",
                )

            except Exception as error:
                messages.error(request, str(error))

            finally:
                _cleanup(*temp_paths, output_path)

    else:
        form = SingleFileForm()

    job_stack = _get_job_stack(request, "image-to-pdf", job)

    return render(request, "document_toolkit/image_to_pdf.html", {
        "form": form,
        "job_stack": job_stack,
        "tool_title": "Image to PDF",
        "tool_description": "Combine one or more images into a single PDF.",
        "tool_icon": "bi-file-earmark-image",
        "tool_accent": "amber",
    })


# ============================================================
# JOB HISTORY -- DELETE
# ============================================================

@login_required
def delete_job(request, pk):

    job = get_object_or_404(ToolJob, pk=pk, user=request.user)

    if request.method == "POST":
        job.delete()
        messages.success(request, "Removed from history.")

    return redirect("document_toolkit:home")
