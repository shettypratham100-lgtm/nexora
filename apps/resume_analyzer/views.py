"""
Resume Analyzer Views
"""

import os
import tempfile

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from services.resume.resume_processor import process_resume

from .forms import ResumeUploadForm
from .models import ResumeAnalysis


# ==========================================================
# UPLOAD RESUME
# ==========================================================

@login_required
def upload_resume(request):
    """
    Upload and analyze a resume.

    Workflow
    --------
    Upload
        ↓
    Temporary File
        ↓
    Resume Processor
        ↓
    Save Analysis
        ↓
    Delete Temporary File
        ↓
    Result Page
    """

    if request.method == "POST":

        form = ResumeUploadForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            uploaded_file = form.cleaned_data["resume"]

            temp_path = None

            try:

                # --------------------------------------------------
                # Save uploaded resume temporarily
                # --------------------------------------------------

                suffix = os.path.splitext(
                    uploaded_file.name
                )[1].lower()

                with tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=suffix
                ) as temp_file:

                    for chunk in uploaded_file.chunks():
                        temp_file.write(chunk)

                    temp_path = temp_file.name

                # --------------------------------------------------
                # Process Resume
                # --------------------------------------------------

                analysis = process_resume(
                    user=request.user,
                    file_path=temp_path
                )

                # --------------------------------------------------
                # Redirect to Result
                # --------------------------------------------------

                return redirect(
                    "resume_result",
                    analysis.id
                )

            finally:

                # --------------------------------------------------
                # Delete Temporary Resume
                # --------------------------------------------------

                if (
                    temp_path
                    and os.path.exists(temp_path)
                ):
                    os.remove(temp_path)

    else:

        form = ResumeUploadForm()

    return render(
        request,
        "resume_analyzer/upload_resume.html",
        {
            "form": form
        }
    )


# ==========================================================
# RESUME RESULT
# ==========================================================

@login_required
def resume_result(
    request,
    analysis_id
):
    """
    Display a previously generated
    Resume Intelligence Report.
    """

    analysis = get_object_or_404(
        ResumeAnalysis,
        id=analysis_id,
        user=request.user
    )

    return render(
        request,
        "resume_analyzer/result.html",
        {
            "analysis": analysis
        }
    )


# ==========================================================
# RESUME HISTORY
# ==========================================================

@login_required
def resume_history(request):
    """
    List every past Resume Intelligence Report for the
    logged-in user, newest first, with each one's score
    compared against the analysis before it so trends over
    time are visible at a glance.
    """

    analyses = list(
        ResumeAnalysis.objects.filter(user=request.user)
    )

    # analyses is newest-first (model default ordering), so the
    # "previous" analysis for trend comparison is the next item
    # in this same list, not the one before it.
    for index, analysis in enumerate(analyses):

        try:
            analysis.overall_score = analysis.ai_recommendations.get(
                "overall_resume_score", {}
            ).get("score")
        except AttributeError:
            analysis.overall_score = None

        try:
            analysis.ats_score_value = analysis.ai_recommendations.get(
                "ats_score", {}
            ).get("score")
        except AttributeError:
            analysis.ats_score_value = None

        analysis.score_delta = None

        has_older_analysis = index + 1 < len(analyses)

        if has_older_analysis and analysis.overall_score is not None:

            older_analysis = analyses[index + 1]

            try:
                older_score = older_analysis.ai_recommendations.get(
                    "overall_resume_score", {}
                ).get("score")
            except AttributeError:
                older_score = None

            if older_score is not None:
                analysis.score_delta = analysis.overall_score - older_score

    return render(
        request,
        "resume_analyzer/history.html",
        {
            "analyses": analyses,
        }
    )


# ==========================================================
# DELETE RESUME ANALYSIS
# ==========================================================

@login_required
def delete_resume_analysis(
    request,
    analysis_id
):
    """
    Permanently delete a past Resume Intelligence Report.
    """

    analysis = get_object_or_404(
        ResumeAnalysis,
        id=analysis_id,
        user=request.user
    )

    if request.method == "POST":

        analysis.delete()

        messages.success(
            request,
            "Resume analysis deleted."
        )

    return redirect("resume_history")