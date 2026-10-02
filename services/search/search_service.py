"""
Search Service

Provides centralized search functionality for resources.

Responsibilities
----------------
1. Search resources belonging to the current user.
2. Search across multiple fields.
3. Return matching resources ordered by newest first.
"""

from django.db.models import (
    Case,
    IntegerField,
    Q,
    Value,
    When,
)

from apps.resource_manager.models import Resource


def search_resources(user, query):
    """
    Search resources owned by a user.

    Parameters
    ----------
    user : User
        Currently logged-in user.

    query : str
        Search text entered by the user.

    Returns
    -------
    QuerySet
        Matching Resource objects.
    """

    # Remove unnecessary spaces.
    query = query.strip()

    # Empty search -> no results.
    if not query:
        return Resource.objects.none()

    return (
    Resource.objects.filter(
        collection__user=user
    )
    .annotate(

        relevance=

        # Highest priority
        Case(
            When(title__icontains=query, then=Value(40)),
            default=Value(0),
            output_field=IntegerField(),
        )

        +

        # High priority
        Case(
            When(keywords__icontains=query, then=Value(30)),
            default=Value(0),
            output_field=IntegerField(),
        )

        +

        # Medium priority
        Case(
            When(summary__icontains=query, then=Value(20)),
            default=Value(0),
            output_field=IntegerField(),
        )

        +

        # Lowest priority
        Case(
            When(description__icontains=query, then=Value(10)),
            default=Value(0),
            output_field=IntegerField(),
        )

    )
    .filter(relevance__gt=0)
    .select_related("collection")
    .order_by("-relevance", "-created_at")
)