from pathlib import Path
from django.http import FileResponse, Http404
import os
from django.db.models import Q
import mimetypes
from django.conf import settings
from django.utils import timezone
from .services.preview import get_preview_pdf
from .services.preview import (
    get_preview_pdf,
    IMAGE_EXTENSIONS,
)
from .services.storage import (
    get_storage_usage,
    has_room_for,
    move_resource_to_trash,
    move_collection_to_trash,
    restore_resource,
    restore_collection,
    purge_expired_trash,
)
import threading
from services.ai.ai_processor import process_resource_by_id
from django.http import JsonResponse
from django.urls import reverse
# =====================================================
# RESOURCE MANAGER VIEWS
# =====================================================
#
# Views receive HTTP requests from users,
# perform the required processing,
# and return an HTTP response.
#
# In our case,
# most responses will be HTML pages.
# =====================================================


# =====================================================
# IMPORTS
# =====================================================

# login_required
#
# This decorator ensures that only authenticated
# (logged-in) users can access a view.
#
# If the user is not logged in,
# Django automatically redirects them
# to the login page.
from django.contrib.auth.decorators import login_required


# render()
#
# Used to return an HTML template
# as the response.
#
# Syntax:
#
# render(request, template_name, context)
#
# request
#     Current user's HTTP request.
#
# template_name
#     HTML file to display.
#
# context
#     Optional data sent to the template.
#
from django.shortcuts import render,redirect, get_object_or_404


# =====================================================
# COLLECTION LIST VIEW
# =====================================================
#
# Displays all collections created by the
# currently logged-in user.
#
# URL:
#
# /resources/collections/
# =====================================================

# Import Collection model
from .models import Collection, Resource, RecentSearch


@login_required
def collection_list(request):

    # =============================================
    # FETCH USER COLLECTIONS
    # =============================================
    #
    # request.user
    #     Currently logged-in user.
    #
    # filter()
    #     Retrieves only the collections
    #     that belong to this user.
    #
    # annotate(resource_count=...)
    #     Active (non-trashed) resource count per
    #     collection, computed in the DB instead of
    #     the template hitting collection.resources.count
    #     (which would include trashed resources and
    #     run one extra query per row).
    #
    from django.db.models import Count, Q

    collections = Collection.objects.filter(
        user=request.user,
        is_deleted=False,
    ).annotate(
        resource_count=Count("resources", filter=Q(resources__is_deleted=False))
    ).order_by("-created_at")

    # =============================================
    # RENDER TEMPLATE
    # =============================================
    #
    # Send collections to the template.
    #
    return render(
        request,
        "resource_manager/collections.html",
        {
            "collections": collections,
        }
    )


# =====================================================
# CREATE COLLECTION VIEW
# =====================================================
#
# Handles both:
#
# GET Request
#     Displays the Create Collection form.
#
# POST Request
#     Validates the submitted form and
#     saves the collection into the database.
#
# URL:
#
# /resources/collections/create/
# =====================================================

from django.contrib import messages

from .forms import CollectionForm, ResourceForm


@login_required
def create_collection(request):

    # =============================================
    # FORM SUBMISSION
    # =============================================
    #
    # When the user clicks the Submit button,
    # the browser sends a POST request.
    #
    if request.method == "POST":

        # Create the form using submitted data.
        form = CollectionForm(request.POST)

        # Check whether all form fields are valid.
        if form.is_valid():

            # -----------------------------------------
            # commit=False
            # -----------------------------------------
            #
            # Creates the Collection object
            # but DOES NOT save it yet.
            #
            # We need this because we still have to
            # assign the logged-in user.
            #
            collection = form.save(commit=False)

            # Assign the current logged-in user.
            collection.user = request.user

            # Save the object to the database.
            collection.save()

            # Display a success message.
            messages.success(
                request,
                "Collection created successfully."
            )

            # Redirect the user to the collections page.
            return redirect(
                "resource_manager:collection_list"
            )

    # =============================================
    # DISPLAY EMPTY FORM
    # =============================================
    #
    # Runs when:
    #
    # • User opens the page for the first time.
    #
    # OR
    #
    # • Form validation fails.
    #
    else:

        form = CollectionForm()

    # =============================================
    # RETURN TEMPLATE
    # =============================================
    #
    # Send the form to the HTML template.
    #
    return render(
        request,
        "resource_manager/create_collection.html",
        {
            "form": form,
        }
    )

@login_required
def edit_collection(request, pk):

    # =================================================
    # EDIT COLLECTION
    # =================================================
    #
    # Allows the logged-in user to update an existing
    # collection.
    #
    # Only collections belonging to the current user
    # can be edited.
    #
    # =================================================

    # ---------------------------------------------
    # Retrieve the requested collection.
    #
    # If:
    # • The collection doesn't exist, OR
    # • It belongs to another user,
    #
    # Django automatically returns a 404 page.
    # ---------------------------------------------

    collection = get_object_or_404(
        Collection,
        pk=pk,
        user=request.user,
    )

    # ---------------------------------------------
    # Handle form submission.
    # ---------------------------------------------

    if request.method == "POST":

        form = CollectionForm(
            request.POST,
            instance=collection,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Collection updated successfully."
            )

            return redirect(
                "resource_manager:collection_list"
            )

    # ---------------------------------------------
    # Display existing collection information.
    # ---------------------------------------------

    else:

        form = CollectionForm(
            instance=collection,
        )

    # ---------------------------------------------
    # Render edit page.
    # ---------------------------------------------

    return render(
        request,
        "resource_manager/edit_collection.html",
        {
            "form": form,
            "collection": collection,
        },
    )

@login_required
def delete_collection(request, pk):

    # =================================================
    # DELETE COLLECTION
    # =================================================
    #
    # Deletes a collection belonging to the currently
    # logged-in user.
    #
    # =================================================

    collection = get_object_or_404(
        Collection,
        pk=pk,
        user=request.user,
    )

    if request.method == "POST":

        move_collection_to_trash(collection)

        messages.success(
            request,
            f"Collection moved to Trash. It will be permanently deleted in {settings.TRASH_RETENTION_DAYS} days."
        )

        return redirect(
            "resource_manager:collection_list"
        )

    return render(
        request,
        "resource_manager/delete_collection.html",
        {
            "collection": collection,
            "retention_days": settings.TRASH_RETENTION_DAYS,
        }
    )


# =====================================================
# COLLECTION DETAIL VIEW
# =====================================================
#
# Displays a single collection and,
# later, all resources inside it.
#
# URL:
#
# /resources/collections/<id>/
# =====================================================

@login_required
def collection_detail(request, pk):

    # =============================================
    # FETCH COLLECTION
    # =============================================
    #
    # get_object_or_404()
    #
    # Searches for one Collection matching:
    #
    # id = pk
    # user = logged-in user
    #
    # If no matching collection exists,
    # Django returns a 404 page.
    #
    collection = get_object_or_404(
        Collection,
        pk=pk,
        user=request.user,
        is_deleted=False,
    )

    resources = collection.resources.filter(is_deleted=False)

    # =============================================
    # RENDER TEMPLATE
    # =============================================
    #
    # Pass the collection object
    # to the HTML template.
    #
    return render(
        request,
        "resource_manager/collection_detail.html",
        {
            "collection": collection,
            "resources": resources,
        },
    )


# =====================================================
# UPLOAD RESOURCE VIEW
# =====================================================
#
# Handles:
#
# GET Request
#     Display upload form.
#
# POST Request
#     Validate and save resource.
#
# Supports:
#
# • File Uploads
# • External URLs
#
# URL:
#
# /resources/upload/
# =====================================================

@login_required
def upload_resource(request, pk=None):

    # =================================================
    # DETERMINE THE TARGET COLLECTION
    # =================================================
    #
    # If the upload is initiated from a collection page,
    # retrieve that collection.
    #
    # Otherwise, keep it as None so the user can choose
    # from the dropdown.
    #

    collection = None

    if pk is not None:

        collection = get_object_or_404(
            Collection,
            pk=pk,
            user=request.user,
        )

    # =============================================
    # FORM SUBMISSION
    # =============================================

    if request.method == "POST":

        # -----------------------------------------
        # request.POST
        #
        # Contains normal form data.
        #
        # request.FILES
        #
        # Contains uploaded files.
        #
        # user=request.user
        #
        # Used to filter the collection dropdown.
        # -----------------------------------------

        form = ResourceForm(
            request.POST,
            request.FILES,
            user=request.user,
            collection=collection,
        )

        # =============================================
        # VALIDATE FORM
        # =============================================
        #
        # Check whether all submitted data is valid.
        #
        if form.is_valid():

            # -------------------------------------------------
            # STORAGE QUOTA CHECK
            #
            # Only file uploads count against storage -- links
            # (YouTube, websites, Drive) don't use any of the
            # user's allowance.
            # -------------------------------------------------

            uploaded_file = request.FILES.get("file")

            if uploaded_file and not has_room_for(request.user, uploaded_file.size):

                usage = get_storage_usage(request.user)

                messages.error(
                    request,
                    f"You've used {usage['used_gb']} GB of your {usage['limit_gb']} GB storage limit. "
                    "Free up space by emptying Trash or deleting resources you don't need."
                )

                return render(
                    request,
                    "resource_manager/upload_resource.html",
                    {
                        "form": form,
                        "collection": collection,
                    },
                )

            # -----------------------------------------
            # SAVE RESOURCE
            # -----------------------------------------
            #
            # form.save() creates a new Resource object
            # in the database.
            #
            # Instead of ignoring the returned object,
            # we store it in a variable because we'll
            # need its collection information for
            # redirection.
            #
            resource = form.save(commit=False)

            # -------------------------------------------------
            # If the upload originated from a collection page,
            # assign the collection automatically.
            # -------------------------------------------------

            if collection is not None:

                resource.collection = collection

            resource.save()
            # -------------------------------------------------
            # Automatically generate AI summary and keywords.
            #
            # AI failures should never prevent the resource
            # from being uploaded.
            # -------------------------------------------------
            # -------------------------------------------------
            # Process AI in the background so the user doesn't
            # have to wait for Gemini to finish.
            # -------------------------------------------------
            threading.Thread(
                target=process_resource_by_id,
                args=(resource.pk,),
                daemon=True,
            ).start()

            # -----------------------------------------
            # SUCCESS MESSAGE
            # -----------------------------------------
            #
            # Display a success notification to the user.
            #
            messages.success(
                request,
                "Resource uploaded successfully."
            )

            # -----------------------------------------
            # REDIRECT TO COLLECTION DETAIL
            # -----------------------------------------
            #
            # resource.collection
            #     Returns the Collection object to which
            #     this resource belongs.
            #
            # resource.collection.pk
            #     Returns the primary key (ID) of that
            #     collection.
            #
            # Example:
            #
            # Collection ID = 5
            #
            # Redirects to:
            #
            # /resources/collections/5/
            #
            return redirect(
                "resource_manager:collection_detail",
                resource.collection.pk,
            )

    # =============================================
    # DISPLAY EMPTY FORM
    # =============================================

    else:

        form = ResourceForm(
            user=request.user,
            collection=collection,
        )

    # =============================================
    # RENDER TEMPLATE
    # =============================================

    return render(
        request,
        "resource_manager/upload_resource.html",
        {
            "form": form,
            "collection": collection,
        },
    )


# =====================================================
# EDIT RESOURCE
# =====================================================
#
# Allows users to update an existing resource.
#
# Features:
# - Only the owner can edit the resource.
# - Existing values are pre-filled.
# - Users can update file or external URL.
# =====================================================

@login_required
def edit_resource(request, pk):

    # ---------------------------------------------
    # Get the requested resource
    # ---------------------------------------------

    resource = get_object_or_404(
        Resource,
        pk=pk,
        collection__user=request.user
    )

    # ---------------------------------------------
    # Handle form submission
    # ---------------------------------------------

    if request.method == "POST":

        form = ResourceForm(
            request.POST,
            request.FILES,
            instance=resource,
            user=request.user,
            collection=resource.collection
        )

        if form.is_valid():

            print("========== VALID ==========")

            updated_resource = form.save(commit=False)

            # Preserve the existing collection.
            updated_resource.collection = resource.collection

            updated_resource.save()

            messages.success(
                request,
                "Resource updated successfully."
            )

            return redirect(
                "resource_manager:collection_detail",
                pk=resource.collection.pk
            )

        else:

            print("========== INVALID ==========")
            print(form.errors)

    # ---------------------------------------------
    # Display existing resource
    # ---------------------------------------------

    else:

        form = ResourceForm(
            instance=resource,
            user=request.user,
            collection=resource.collection
        )


    return render(
        request,
        "resource_manager/edit_resource.html",
        {
            "form": form,
            "resource": resource,
            "collection": resource.collection,
        }
    )


@login_required
def delete_resource(request, pk):

    # ==================================================
    # DELETE RESOURCE
    # ==================================================
    #
    # Deletes a single resource belonging to the
    # currently logged-in user.
    #
    # A confirmation page is shown before deletion.
    #
    # The uploaded file is automatically removed from
    # the media folder by the post_delete signal.
    #
    # ==================================================

    resource = get_object_or_404(
        Resource,
        pk=pk,
        collection__user=request.user,
    )

    if request.method == "POST":

        collection_id = resource.collection.pk

        move_resource_to_trash(resource)

        messages.success(
            request,
            f"Resource moved to Trash. It will be permanently deleted in {settings.TRASH_RETENTION_DAYS} days."
        )

        return redirect(
            "resource_manager:collection_detail",
            pk=collection_id,
        )

    return render(
        request,
        "resource_manager/delete_resource.html",
        {
            "resource": resource,
            "retention_days": settings.TRASH_RETENTION_DAYS,
        },
    )

# =====================================================
# VIEW RESOURCE
# =====================================================
#
# Displays a resource based on its file type.
#
# Supported
#
# • PDF
# • Images
#
# Future
#
# • DOCX
# • PPT
# • Videos
# • YouTube
# • Websites
#
# =====================================================
@login_required
def view_resource(request, pk):

    resource = get_object_or_404(
        Resource,
        pk=pk,
        collection__user=request.user
    )

    file_extension = ""

    if resource.file:

        file_extension = (
            Path(resource.file.name)
            .suffix
            .lower()
        )

    context = {

        "resource": resource,
        "file_extension": file_extension

    }

    return render(
        request,
        "resource_manager/view_resource.html",
        context
    )


# =====================================================
# STREAM PDF
# =====================================================
#
# Streams a PDF file inside the browser.
#
# Used by the Resource Viewer.
#
# Future:
# • PDF
# • Converted DOCX
# • Converted PPT
#
# =====================================================

@login_required
def stream_pdf(request, pk):

    resource = get_object_or_404(

        Resource,

        pk=pk,

        collection__user=request.user

    )

    # ---------------------------------------------
    # Determine the uploaded file extension.
    # ---------------------------------------------

    extension = Path(resource.file.path).suffix.lower()

    # ---------------------------------------------
    # If the uploaded file is an image,
    # stream it directly without converting it.
    # ---------------------------------------------

    if extension in IMAGE_EXTENSIONS:

        mime_type, _ = mimetypes.guess_type(resource.file.path)

        response = FileResponse(

            open(resource.file.path, "rb"),

            content_type=mime_type or "application/octet-stream"

        )

        response["Content-Disposition"] = "inline"

        return response

    # ---------------------------------------------
    # Generate (or retrieve) the preview PDF.
    #
    # If the uploaded file is already a PDF,
    # get_preview_pdf() simply returns the original
    # PDF path.
    #
    # If the uploaded file is a DOC, DOCX, PPT or
    # PPTX, it converts it to PDF (only once),
    # caches the preview and returns its path.
    # ---------------------------------------------

    preview_pdf = get_preview_pdf(resource)

    # ---------------------------------------------
    # Ensure the preview PDF exists.
    # ---------------------------------------------

    if not preview_pdf.exists():

        raise Http404("File not found.")

    # ---------------------------------------------
    # Stream the preview PDF to the browser.
    # ---------------------------------------------

    response = FileResponse(

        open(preview_pdf, "rb"),

        content_type="application/pdf"

    )

    # ---------------------------------------------
    # Display inside the browser instead of forcing
    # a download.
    # ---------------------------------------------

    response["Content-Disposition"] = (
        'inline; filename="preview.pdf"'
    )

    return response

from pathlib import Path
from django.shortcuts import render

from .services.preview import IMAGE_EXTENSIONS


from pathlib import Path

from .services.preview import IMAGE_EXTENSIONS


@login_required
def view_resource(request, pk):

    resource = get_object_or_404(

        Resource,

        pk=pk,

        collection__user=request.user

    )

    # ---------------------------------------------
    # Determine whether the uploaded file is an
    # image so the template knows whether to show
    # an <img> tag or the PDF.js viewer.
    # ---------------------------------------------

    is_image = False

    if resource.file:

        extension = Path(resource.file.path).suffix.lower()

        is_image = extension in IMAGE_EXTENSIONS

    return render(

        request,

        "resource_manager/view_resource.html",

        {

            "resource": resource,

            "is_image": is_image,

        }

    )

# =====================================================
# SEARCH RESOURCES
# =====================================================
#
# Allows users to search their own resources.
#
# Searches:
#
# • Title
# • Description
# • AI Summary
# • AI Keywords
#
# URL:
#
# /resources/search/
# =====================================================

@login_required
def resource_preview(request, pk):
    """
    Return a small JSON response containing
    the resource preview shown on hover.
    """

    resource = get_object_or_404(
        Resource,
        pk=pk,
        collection__user=request.user,
    )

    return JsonResponse({
        "title": resource.title,
        "type": resource.get_resource_type_display(),
        "summary": resource.summary,
        "keywords": resource.keywords,
        "status": resource.ai_status,
    })

@login_required
def search_resources_view(request):
    """
    Global resource search.

    Users can search by:
    • Title
    • Description
    • AI Summary
    • AI Keywords
    """

    # ======================================================
    # GET SEARCH QUERY
    # ======================================================

    query = request.GET.get("q", "").strip()

    results = Resource.objects.none()

    # ======================================================
    # SEARCH RESOURCES
    # ======================================================

    if query:

        results = Resource.objects.filter(

            collection__user=request.user

        ).filter(

            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(summary__icontains=query) |
            Q(keywords__icontains=query)

        ).distinct()

        # ======================================================
        # REMOVE DUPLICATE SEARCH
        # ======================================================

        RecentSearch.objects.filter(

            user=request.user,
            query__iexact=query,

        ).delete()

        # ======================================================
        # SAVE NEW SEARCH
        # ======================================================

        RecentSearch.objects.create(

            user=request.user,

            query=query,

        )

        # ======================================================
        # KEEP ONLY THE LATEST 5 SEARCHES
        # ======================================================

        old_searches = RecentSearch.objects.filter(

            user=request.user

        ).order_by("-searched_at")

        ids_to_delete = [

            search.id

            for search in old_searches[5:]

        ]

        if ids_to_delete:

            RecentSearch.objects.filter(

                id__in=ids_to_delete

            ).delete()

    # ======================================================
    # RENDER SEARCH PAGE
    # ======================================================

    return render(

        request,

        "resource_manager/search_results.html",

        {

            "query": query,

            "results": results,

        }

    )

@login_required
def search_suggestions(request):
    """
    Returns live search suggestions as JSON.

    Used by the global navbar search.
    """

    query = request.GET.get("q", "").strip()

    if not query:

        return JsonResponse([], safe=False)

    resources = Resource.objects.filter(

        collection__user=request.user

    ).filter(

        Q(title__icontains=query) |
        Q(description__icontains=query) |
        Q(summary__icontains=query) |
        Q(keywords__icontains=query)

    )[:6]

    suggestions = []

    for resource in resources:

        # Decide destination
        if resource.external_url:

            url = resource.external_url

        else:

            url = reverse(

                "resource_manager:view_resource",

                args=[resource.pk]

            )

        suggestions.append({

            "id": resource.pk,

            "title": resource.title,

            "type": resource.get_resource_type_display(),

            "url": url,

            "collection": resource.collection.name,

            "external": bool(resource.external_url),

        })

    return JsonResponse(

        suggestions,

        safe=False,

    )

# =====================================================
# TRASH
# =====================================================
#
# Lists soft-deleted collections and resources, with
# "restore" and "delete permanently" actions.
#
# Anything past its retention window is purged the
# moment this page loads.
#
# URL: /resources/trash/
# =====================================================

@login_required
def trash_list(request):

    purge_expired_trash(request.user)

    cutoff_days = settings.TRASH_RETENTION_DAYS

    trashed_collections = Collection.objects.filter(
        user=request.user,
        is_deleted=True,
    )

    trashed_resources = Resource.objects.filter(
        collection__user=request.user,
        is_deleted=True,
    )

    # Attach a "days_left" number to each item for display.
    for item in list(trashed_collections) + list(trashed_resources):
        elapsed = timezone.now() - item.deleted_at
        item.days_left = max(cutoff_days - elapsed.days, 0)

    return render(
        request,
        "resource_manager/trash.html",
        {
            "trashed_collections": trashed_collections,
            "trashed_resources": trashed_resources,
            "retention_days": cutoff_days,
        },
    )


@login_required
def restore_resource_view(request, pk):

    resource = get_object_or_404(
        Resource,
        pk=pk,
        collection__user=request.user,
        is_deleted=True,
    )

    if request.method == "POST":

        restore_resource(resource)
        messages.success(request, f'"{resource.title}" restored.')

    return redirect("resource_manager:trash")


@login_required
def restore_collection_view(request, pk):

    collection = get_object_or_404(
        Collection,
        pk=pk,
        user=request.user,
        is_deleted=True,
    )

    if request.method == "POST":

        restore_collection(collection)
        messages.success(request, f'"{collection.name}" restored.')

    return redirect("resource_manager:trash")


@login_required
def permanent_delete_resource_view(request, pk):

    resource = get_object_or_404(
        Resource,
        pk=pk,
        collection__user=request.user,
        is_deleted=True,
    )

    if request.method == "POST":

        resource.delete()
        messages.success(request, "Resource permanently deleted.")

    return redirect("resource_manager:trash")


@login_required
def permanent_delete_collection_view(request, pk):

    collection = get_object_or_404(
        Collection,
        pk=pk,
        user=request.user,
        is_deleted=True,
    )

    if request.method == "POST":

        collection.delete()
        messages.success(request, "Collection permanently deleted.")

    return redirect("resource_manager:trash")


@login_required
def empty_trash_view(request):

    if request.method == "POST":

        Resource.objects.filter(
            collection__user=request.user,
            is_deleted=True,
        ).delete()

        Collection.objects.filter(
            user=request.user,
            is_deleted=True,
        ).delete()

        messages.success(request, "Trash emptied.")

    return redirect("resource_manager:trash")


# =====================================================
# STARRED
# =====================================================

@login_required
def starred_list(request):

    starred_collections = Collection.objects.filter(
        user=request.user,
        is_deleted=False,
        is_starred=True,
    )

    starred_resources = Resource.objects.filter(
        collection__user=request.user,
        is_deleted=False,
        is_starred=True,
    )

    return render(
        request,
        "resource_manager/starred.html",
        {
            "starred_collections": starred_collections,
            "starred_resources": starred_resources,
        },
    )


@login_required
def toggle_star_resource(request, pk):

    resource = get_object_or_404(
        Resource,
        pk=pk,
        collection__user=request.user,
    )

    if request.method == "POST":

        resource.is_starred = not resource.is_starred
        resource.save(update_fields=["is_starred"])

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"is_starred": resource.is_starred})

    return redirect(request.META.get("HTTP_REFERER", "resource_manager:collection_list"))


@login_required
def toggle_star_collection(request, pk):

    collection = get_object_or_404(
        Collection,
        pk=pk,
        user=request.user,
    )

    if request.method == "POST":

        collection.is_starred = not collection.is_starred
        collection.save(update_fields=["is_starred"])

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"is_starred": collection.is_starred})

    return redirect(request.META.get("HTTP_REFERER", "resource_manager:collection_list"))
