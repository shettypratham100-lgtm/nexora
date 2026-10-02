# ==========================================================
# DJANGO SIGNALS
# ==========================================================
#
# Signals allow us to execute specific code automatically
# when certain events occur in Django.
#
# In this file, we use the post_delete signal to ensure
# that uploaded resource files are removed from the
# media folder whenever a Resource object is deleted.
#
# This prevents orphaned files from occupying storage.
#
# ==========================================================

# Import the post_delete signal.
# This signal is triggered immediately after an object
# is deleted from the database.
from django.db.models.signals import post_delete

# Import the receiver decorator.
# It connects a function to a specific signal.
from django.dispatch import receiver

# Import the Resource model.
# We want to monitor deletion events for this model.
from .models import Resource


# ==========================================================
# DELETE UPLOADED FILE AFTER RESOURCE DELETION
# ==========================================================
#
# This function is automatically executed whenever a
# Resource object is deleted.
#
# It works for:
#
# ✔ Deleting an individual resource.
#
# ✔ Deleting a collection that contains multiple resources
#   (Cascade Delete).
#
# Without this signal:
#
# Database Record  -> Deleted ✅
#
# Uploaded File    -> Still remains in media folder ❌
#
# This causes unnecessary storage usage.
#
# The signal ensures that both the database record
# and the uploaded file are removed together.
#
# ==========================================================

@receiver(post_delete, sender=Resource)
def delete_resource_file(sender, instance, **kwargs):

    # ------------------------------------------------------
    # Check whether the resource has an uploaded file.
    # ------------------------------------------------------

    if instance.file:

        # --------------------------------------------------
        # Delete the uploaded file from the configured
        # storage system.
        #
        # save=False prevents Django from attempting to
        # save the model again after deleting the file.
        # --------------------------------------------------

        instance.file.delete(save=False)