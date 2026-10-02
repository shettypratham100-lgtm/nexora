# =====================================================
# RESOURCE MANAGER URL CONFIGURATION
# =====================================================
#
# This file maps URL paths to their corresponding
# view functions.
#
# Example:
#
# User visits:
# /resources/collections/
#
# Django looks inside this file and calls the
# appropriate view function.
# =====================================================


# Import the 'path' function used to create URL routes.
from django.urls import path

# Import views from the current app.
#
# The '.' means:
# "Import the views.py file from the current folder."
from . import views


# Namespace for this app.
#
# This prevents conflicts if another app also has
# a URL named "create".
#
# Example:
#
# resource_manager:create_collection
#
# instead of simply:
#
# create_collection
app_name = "resource_manager"


# =====================================================
# URL PATTERNS
# =====================================================
#
# Every URL of this module is registered here.
# =====================================================

urlpatterns = [

    # =================================================
    # COLLECTION LIST
    # =================================================
    #
    # URL:
    #
    # /resources/collections/
    #
    # Calls:
    #
    # collection_list()
    #
    # Name:
    #
    # resource_manager:collection_list
    #
    path(
        "collections/",
        views.collection_list,
        name="collection_list",
    ),

    # =================================================
    # CREATE COLLECTION
    # =================================================
    #
    # URL:
    #
    # /resources/collections/create/
    #
    # Calls:
    #
    # create_collection()
    #
    # Name:
    #
    # resource_manager:create_collection
    #
    path(
        "collections/create/",
        views.create_collection,
        name="create_collection",
    ),

    # =================================================
    # COLLECTION DETAILS
    # =================================================
    #
    # URL:
    #
    # /resources/collections/5/
    #
    # <int:pk>
    #     Captures an integer from the URL and
    #     passes it to the view as "pk".
    #
    path(
        "collections/<int:pk>/",
        views.collection_detail,
        name="collection_detail",
    ),
    # =====================================================
    # EDIT COLLECTION
    # =====================================================
    #
    # URL:
    #
    # /resources/collections/5/edit/
    #
    # Allows the user to update the collection name
    # and description.
    #
    path(
        "collections/<int:pk>/edit/",
        views.edit_collection,
        name="edit_collection",
    ),

    # =====================================================
    # DELETE COLLECTION
    # =====================================================
    #
    # URL:
    #
    # /resources/collections/5/delete/
    #
    # Permanently deletes a collection.
    #
    path(
        "collections/<int:pk>/delete/",
        views.delete_collection,
        name="delete_collection",
    ),

    # =================================================
    # GLOBAL UPLOAD RESOURCE
    # =================================================
    #
    # URL:
    #
    # /resources/upload/
    #
    # Used when the user uploads a resource from
    # the sidebar.
    #
    path(
        "upload/",
        views.upload_resource,
        name="upload_resource",
    ),

    # =================================================
    # UPLOAD RESOURCE TO COLLECTION
    # =================================================
    #
    # URL:
    #
    # /resources/collections/5/upload/
    #
    # Used when the user uploads a resource from
    # inside a specific collection.
    #
    path(
        "collections/<int:pk>/upload/",
        views.upload_resource,
        name="collection_upload",
    ),

    # =====================================================
    # EDIT RESOURCE
    # =====================================================
    #
    # Allows users to update an existing resource.
    #
    # Example:
    # /resources/15/edit/
    #
    # =====================================================

    path(
        "<int:pk>/edit/",
        views.edit_resource,
        name="edit_resource",
    ),

    # =====================================================
    # DELETE RESOURCE
    # =====================================================
    #
    # Permanently deletes a resource.
    #
    path(
        "resource/<int:pk>/delete/",
        views.delete_resource,
        name="delete_resource",
    ),

    # =====================================================
    # VIEW RESOURCE
    # =====================================================
    #
    # Displays a resource inside Nexora.
    #
    # Depending on the resource type, the page will
    # display:
    #
    # • PDF Viewer
    # • Image Viewer
    # • YouTube Player
    # • Website Link
    #
    # Future:
    #
    # DOCX/PPT will first be converted into temporary
    # PDFs before being displayed.
    #
    path(
        "resource/<int:pk>/",
        views.view_resource,
        name="view_resource",
    ),

    path(
    "resource/<int:pk>/pdf/",
    views.stream_pdf,
    name="stream_pdf",
    ),

    path(
        "search/",
        views.search_resources_view,
        name="search_resources",
    ),

    path(
        "preview/<int:pk>/",
        views.resource_preview,
        name="resource_preview",
    ),

    path(
        "search-suggestions/",
        views.search_suggestions,
        name="search_suggestions",

    ),

    # =====================================================
    # TRASH
    # =====================================================

    path("trash/", views.trash_list, name="trash"),
    path("trash/empty/", views.empty_trash_view, name="empty_trash"),

    path("resource/<int:pk>/restore/", views.restore_resource_view, name="restore_resource"),
    path("collections/<int:pk>/restore/", views.restore_collection_view, name="restore_collection"),

    path("resource/<int:pk>/delete-permanently/", views.permanent_delete_resource_view, name="permanent_delete_resource"),
    path("collections/<int:pk>/delete-permanently/", views.permanent_delete_collection_view, name="permanent_delete_collection"),

    # =====================================================
    # STARRED
    # =====================================================

    path("starred/", views.starred_list, name="starred"),
    path("resource/<int:pk>/star/", views.toggle_star_resource, name="toggle_star_resource"),
    path("collections/<int:pk>/star/", views.toggle_star_collection, name="toggle_star_collection"),

]