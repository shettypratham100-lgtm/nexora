from django.core.exceptions import ValidationError
# =====================================================
# RESOURCE MANAGER FORMS
# =====================================================
#
# This file contains Django Forms used to
# collect user input.
#
# Instead of writing HTML forms manually,
# Django ModelForms automatically create
# forms based on our models.
# =====================================================


# =====================================================
# IMPORTS
# =====================================================

# Import Django's ModelForm class.
#
# ModelForm automatically creates a form
# using the fields from a database model.
#
# Benefits:
#
# • Less code
# • Automatic validation
# • Easy database saving
#
from django import forms


# Import the Collection model.
#
# Import models used by ModelForms.
from .models import Collection, Resource


# =====================================================
# COLLECTION FORM
# =====================================================
#
# Used for:
#
# • Creating a Collection
# • Editing a Collection (later)
#
# Django automatically generates form fields
# based on the Collection model.
# =====================================================

class CollectionForm(forms.ModelForm):

    class Meta:

        # =============================================
        # MODEL
        # =============================================
        #
        # Specifies which model this form belongs to.
        #
        model = Collection

        # =============================================
        # FIELDS
        # =============================================
        #
        # These model fields will appear
        # in the HTML form.
        #
        # Notice we don't include:
        #
        # user
        # created_at
        # updated_at
        #
        # because Django will handle them.
        #
        fields = [

            "name",

            "description",

        ]

        # =============================================
        # WIDGETS
        # =============================================
        #
        # Widgets customize the appearance
        # of HTML form fields.
        #
        # Here we're adding Bootstrap classes.
        #
        widgets = {

            "name": forms.TextInput(

                attrs={

                    "class": "form-control",

                    "placeholder": "Enter Collection Name",

                }

            ),

            "description": forms.Textarea(

                attrs={

                    "class": "form-control",

                    "rows": 4,

                    "placeholder": "Enter Collection Description",

                }

            ),

        }

# =====================================================
# RESOURCE FORM
# =====================================================
#
# Used for:
#
# • Uploading a new resource
# • Editing an existing resource
#
# Supports:
# • PDF
# • DOCX
# • PPT
# • Images
# • YouTube Links
# • Website Links
# • Google Drive Links
# =====================================================

class ResourceForm(forms.ModelForm):

    # =================================================
    # FORM INITIALIZATION
    # =================================================
    #
    #__init__()

    # Runs automatically whenever a new form object

    # is created.

    # We'll use it to display only the collections

    # belonging to the logged-in user.

    # Example:

    # ResourceForm(user=request.user,collection=collection,)

    # This method customizes the form based on
    # how it was opened.
    #
    # Scenarios:
    #
    # 1. Sidebar Upload
    #
    #    Collection dropdown is visible.
    #
    # 2. Collection Upload
    #
    #    Collection dropdown is hidden because
    #    the collection is already known.
    #
    # =================================================

    def __init__(
        self,
        *args,
        user=None,
        collection=None,
        **kwargs,
    ):

        # Initialize the parent ModelForm.
        super().__init__(*args, **kwargs)

        # ---------------------------------------------
        # SIDEBAR UPLOAD
        # ---------------------------------------------
        #
        # No collection was supplied.
        #
        # Show only this user's collections.
        #
        if collection is None:

            self.fields["collection"].queryset = Collection.objects.filter(
                user=user
            )

        # ---------------------------------------------
        # COLLECTION UPLOAD / EDIT MODE
        # ---------------------------------------------
        #
        # A collection has already been determined.
        #
        # Therefore:
        #
        # • Hide the collection field.
        # • Preselect the existing collection.
        # • Do not require the field during form
        #   validation because it isn't submitted
        #   by the browser.
        #
        else:

            self.fields["collection"].initial = collection

            self.fields["collection"].widget = forms.HiddenInput()

            self.fields["collection"].required = False

    
    # =================================================
    # CUSTOM FORM VALIDATION
    # =================================================
    #
    # Validation Rules:
    #
    # 1. PDF, DOCX, PPT and IMAGE
    #    require a file upload.
    #
    # 2. YOUTUBE, WEBSITE and DRIVE
    #    require an external URL.
    #
    # 3. A resource cannot contain both
    #    a file and an external URL.
    #
    # =================================================

    def clean(self):

        cleaned_data = super().clean()

        resource_type = cleaned_data.get("resource_type")
        uploaded_file = cleaned_data.get("file")
        external_url = cleaned_data.get("external_url")

        # ---------------------------------------------
        # File-based resource types
        # ---------------------------------------------

        file_types = [

            Resource.ResourceType.PDF,

            Resource.ResourceType.DOCX,

            Resource.ResourceType.PPT,

            Resource.ResourceType.IMAGE,

        ]

        # ---------------------------------------------
        # URL-based resource types
        # ---------------------------------------------

        url_types = [

            Resource.ResourceType.YOUTUBE,

            Resource.ResourceType.WEBSITE,

            Resource.ResourceType.DRIVE,

        ]

        # ---------------------------------------------
        # File validation
        # ---------------------------------------------

        if resource_type in file_types:

            # -------------------------------------------------
            # While editing, the resource may already have
            # a file attached. Only require a file if there
            # isn't an existing file and the user hasn't
            # uploaded a new one.
            # -------------------------------------------------

            if not uploaded_file and not self.instance.file:

                self.add_error(
                    "file",
                    "Please upload a file."
                )

            if external_url:

                self.add_error(
                    "external_url",
                    "URL is not required for this resource type."
                )
        # ---------------------------------------------
        # File Extension Validation
        # ---------------------------------------------

        if uploaded_file:

            extension = uploaded_file.name.split(".")[-1].lower()

            allowed_extensions = {

                Resource.ResourceType.PDF: ["pdf"],

                Resource.ResourceType.DOCX: ["doc", "docx"],

                Resource.ResourceType.PPT: ["ppt", "pptx"],

                Resource.ResourceType.IMAGE: [
                    "jpg",
                    "jpeg",
                    "png",
                    "gif",
                    "webp",
                ],

            }

            if resource_type in allowed_extensions:

                if extension not in allowed_extensions[resource_type]:

                    self.add_error(
                        "file",
                        f"Invalid file type. Please upload a {resource_type.lower()} file."
                    )
                    
        # ---------------------------------------------
        # URL validation
        # ---------------------------------------------

        if resource_type in url_types:

            if not external_url and not self.instance.external_url:

                self.add_error(
                    "external_url",
                    "Please enter a valid URL."
                )

            if uploaded_file:

                self.add_error(
                    "file",
                    "File upload is not required for this resource type."
                )

        return cleaned_data

    class Meta:

        # =============================================
        # MODEL
        # =============================================

        model = Resource

        # =============================================
        # FORM FIELDS
        # =============================================
        #
        # collection
        #     Selected collection.
        #
        # title
        #     Resource title.
        #
        # description
        #     Optional description.
        #
        # resource_type
        #     PDF, Image, Website, etc.
        #
        # file
        #     Uploaded file.
        #
        # external_url
        #     External link.
        #
        fields = [

            "collection",

            "title",

            "description",

            "resource_type",

            "file",

            "external_url",

        ]

        # =============================================
        # WIDGETS
        # =============================================

        widgets = {

            "collection": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter Resource Title",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Enter Description",
                }
            ),

            "resource_type": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            # =============================================
            # FILE INPUT
            # =============================================
            #
            # Allows users to upload a new file.
            #
            # During editing, users may replace the
            # existing file by selecting a new one.
            #
            "file": forms.FileInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "external_url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://...",
                }
            ),

        }