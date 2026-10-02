"""
Resume Analyzer URLs
"""

from django.urls import path

from . import views

urlpatterns = [

    # Upload Resume
    path(
        "",
        views.upload_resume,
        name="upload_resume"
    ),

    # Resume Analysis Result
    path(
        "result/<int:analysis_id>/",
        views.resume_result,
        name="resume_result"
    ),

    # Resume History
    path(
        "history/",
        views.resume_history,
        name="resume_history"
    ),

    # Delete Resume Analysis
    path(
        "delete/<int:analysis_id>/",
        views.delete_resume_analysis,
        name="delete_resume_analysis"
    ),

]