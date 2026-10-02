"""
clean_previews.py

Custom Django management command for deleting
expired preview PDFs from the temporary cache.

Usage:
    python manage.py clean_previews
"""

from django.core.management.base import BaseCommand

from apps.resource_manager.services.cleanup import delete_old_previews


class Command(BaseCommand):
    """
    Django management command that removes
    expired preview PDFs.
    """

    # ---------------------------------------------------------
    # Description shown in Django's command list.
    # ---------------------------------------------------------
    help = (
        "Delete expired preview PDFs "
        "from the temporary preview cache."
    )

    # ---------------------------------------------------------
    # Entry point of the command.
    #
    # Running:
    #
    # python manage.py clean_previews
    #
    # automatically executes this method.
    # ---------------------------------------------------------
    def handle(self, *args, **kwargs):

        # -----------------------------------------------------
        # Delete preview PDFs older than the configured age.
        # -----------------------------------------------------
        delete_old_previews()

        # -----------------------------------------------------
        # Display a success message in the terminal.
        # -----------------------------------------------------
        self.stdout.write(

            self.style.SUCCESS(

                "Expired preview PDFs deleted successfully."

            )

        )