"""
Context processors for the Resource Manager.

Provides global data required by templates.

Currently:
    • Recent Searches
    • Storage Usage (for the sidebar widget)
"""

from .models import RecentSearch
from .services.storage import get_storage_usage


def recent_searches(request):
    """
    Makes the user's recent searches available
    to every template.

    Returns:
        recent_searches
    """

    if not request.user.is_authenticated:

        return {
            "recent_searches": []
        }

    return {

        "recent_searches":

        RecentSearch.objects.filter(

            user=request.user

        )[:5]

    }


def storage_usage(request):
    """
    Makes the logged-in user's storage quota usage
    available to every template, for the sidebar's
    storage widget.
    """

    if not request.user.is_authenticated:
        return {"sidebar_storage": None}

    return {"sidebar_storage": get_storage_usage(request.user)}