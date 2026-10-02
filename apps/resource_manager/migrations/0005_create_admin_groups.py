from django.db import migrations


# ==========================================================
# CREATE ADMIN GROUPS
# ==========================================================
#
# This function creates the custom admin roles/groups used
# by Nexora.
#
# The groups allow us to give different administrators
# different levels of access instead of giving everyone
# full superuser permissions.
#
# Groups created:
#
# 1. Content Manager
#    - Can manage resources, collections, recent searches,
#      and document toolkit jobs.
#
# 2. User Manager
#    - Can view and modify users.
#    - Does NOT receive add/delete permissions.
#
# 3. Analyst
#    - Read-only access to resource, resume analysis,
#      collection, and document toolkit information.
#
# ==========================================================


def create_groups(apps, schema_editor):

    # ------------------------------------------------------
    # Get Django's historical versions of these models.
    #
    # We use apps.get_model() instead of importing models
    # directly because migrations must work with the model
    # state that existed when this migration was created.
    # ------------------------------------------------------

    Group = apps.get_model(
        "auth",
        "Group",
    )

    Permission = apps.get_model(
        "auth",
        "Permission",
    )

    ContentType = apps.get_model(
        "contenttypes",
        "ContentType",
    )


    # ======================================================
    # HELPER: GET PERMISSIONS
    # ======================================================
    #
    # Returns Django permissions for a particular model.
    #
    # Example:
    #
    # get_perms(
    #     "resource_manager",
    #     "resource",
    #     ["add", "change", "delete", "view"]
    # )
    #
    # will retrieve:
    #
    # add_resource
    # change_resource
    # delete_resource
    # view_resource
    #
    # ======================================================

    def get_perms(
        app_label,
        model_name,
        actions,
    ):

        try:

            content_type = ContentType.objects.get(
                app_label=app_label,
                model=model_name,
            )

        except ContentType.DoesNotExist:

            # ------------------------------------------------
            # If the model/content type does not exist yet,
            # return an empty permission list instead of
            # causing the migration to fail.
            # ------------------------------------------------

            return []


        return list(
            Permission.objects.filter(
                content_type=content_type,
                codename__in=[
                    f"{action}_{model_name}"
                    for action in actions
                ],
            )
        )


    # ======================================================
    # CONTENT MANAGER
    # ======================================================
    #
    # This role is intended for administrators who manage
    # Nexora's content and document-processing data.
    #
    # Permissions:
    #
    # Resource Manager:
    #   - Collection
    #   - Resource
    #   - RecentSearch
    #
    # Document Toolkit:
    #   - ToolJob
    #
    # Each receives:
    #   - Add
    #   - Change
    #   - Delete
    #   - View
    #
    # ======================================================

    content_manager, _ = Group.objects.get_or_create(
        name="Content Manager",
    )


    content_permissions = []


    # Resource Manager models
    for model_name in [
        "collection",
        "resource",
        "recentsearch",
    ]:

        content_permissions += get_perms(
            "resource_manager",
            model_name,
            [
                "add",
                "change",
                "delete",
                "view",
            ],
        )


    # Document Toolkit
    content_permissions += get_perms(
        "document_toolkit",
        "tooljob",
        [
            "add",
            "change",
            "delete",
            "view",
        ],
    )


    # Assign all collected permissions to the group.
    content_manager.permissions.set(
        content_permissions,
    )


    # ======================================================
    # USER MANAGER
    # ======================================================
    #
    # This role is intended for administrators who need to
    # manage existing users.
    #
    # Permissions:
    #
    #   - View users
    #   - Change users
    #
    # No add/delete permissions are granted here.
    #
    # ======================================================

    user_manager, _ = Group.objects.get_or_create(
        name="User Manager",
    )


    user_manager.permissions.set(
        get_perms(
            "auth",
            "user",
            [
                "change",
                "view",
            ],
        )
    )


    # ======================================================
    # ANALYST
    # ======================================================
    #
    # This role is intended for administrators who only
    # need to inspect Nexora's data.
    #
    # It is a READ-ONLY role.
    #
    # Models:
    #
    # Resource Manager:
    #   - Resource
    #   - Collection
    #
    # Resume Analyzer:
    #   - ResumeAnalysis
    #
    # Document Toolkit:
    #   - ToolJob
    #
    # Only "view" permissions are granted.
    #
    # ======================================================

    analyst, _ = Group.objects.get_or_create(
        name="Analyst",
    )


    analyst_permissions = []


    for app_label, model_name in [

        (
            "resource_manager",
            "resource",
        ),

        (
            "resource_manager",
            "collection",
        ),

        (
            "resume_analyzer",
            "resumeanalysis",
        ),

        (
            "document_toolkit",
            "tooljob",
        ),

    ]:

        analyst_permissions += get_perms(
            app_label,
            model_name,
            [
                "view",
            ],
        )


    # Assign read-only permissions.
    analyst.permissions.set(
        analyst_permissions,
    )


# ==========================================================
# REMOVE ADMIN GROUPS
# ==========================================================
#
# This is the reverse operation for the migration.
#
# If this migration is rolled back, Django will remove
# the three groups created above.
#
# It does NOT delete users.
# It does NOT delete user data.
# It only removes these three permission groups.
#
# ==========================================================


def remove_groups(
    apps,
    schema_editor,
):

    Group = apps.get_model(
        "auth",
        "Group",
    )


    Group.objects.filter(
        name__in=[
            "Content Manager",
            "User Manager",
            "Analyst",
        ]
    ).delete()


# ==========================================================
# MIGRATION DEFINITION
# ==========================================================
#
# IMPORTANT:
#
# This migration previously had an empty dependency.
#
# That caused Django to see:
#
#     0004_collection_deleted_at_collection_is_deleted_and_more
#
# and
#
#     0005_create_admin_groups
#
# as two separate migration branches.
#
# By making 0005 depend on 0004, we tell Django that:
#
#     0004
#       ↓
#     0005
#
# Therefore the migration graph has one proper sequence.
#
# ==========================================================


class Migration(
    migrations.Migration
):


    dependencies = [

        (
            "resource_manager",
            "0004_collection_deleted_at_collection_is_deleted_and_more",
        ),

    ]


    # ======================================================
    # MIGRATION OPERATIONS
    # ======================================================
    #
    # RunPython executes:
    #
    #   create_groups
    #
    # when migrating forward.
    #
    # And:
    #
    #   remove_groups
    #
    # when this migration is reversed.
    #
    # ======================================================

    operations = [

        migrations.RunPython(
            create_groups,
            remove_groups,
        ),

    ]