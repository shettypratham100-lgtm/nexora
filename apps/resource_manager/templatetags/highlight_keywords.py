"""
Template filter for highlighting keywords inside summaries.

Usage
-----

{{ resource.summary|highlight_keywords:resource.keywords|safe }}

Example
-------

Summary:
Flutter is Google's UI toolkit using Dart.

Keywords:
Flutter, Dart

Output:
<strong>Flutter</strong> is Google's UI toolkit using
<strong>Dart</strong>.
"""

import re

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def highlight_keywords(summary, keywords):
    """
    Highlight keywords inside a summary.

    Parameters
    ----------
    summary : str

    keywords : str
        Comma-separated keywords stored in the database.

    Returns
    -------
    SafeString
    """

    if not summary:
        return ""

    if not keywords:
        return summary

    # Split keywords stored like:
    # Flutter, Dart, Stateless Widgets

    keyword_list = [
        keyword.strip()
        for keyword in keywords.split(",")
        if keyword.strip()
    ]

    # Longer keywords first.
    keyword_list.sort(key=len, reverse=True)

    highlighted_summary = summary

    for keyword in keyword_list:

        pattern = re.compile(
            rf"\b({re.escape(keyword)})\b",
            re.IGNORECASE,
        )

        highlighted_summary = pattern.sub(
            r"<strong>\1</strong>",
            highlighted_summary,
        )

    return mark_safe(highlighted_summary)