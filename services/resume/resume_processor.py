"""
Resume Processor

Coordinates the Resume Analyzer pipeline.

Workflow

Resume File
↓
Extract Text
↓
Parse Resume
↓
ONE Gemini Analysis
↓
Save AI Recommendations
"""

from services.document.text_extractor import extract_text
from services.resume.resume_parser import parse_resume
from services.ai.ai_service import analyze_resume

from apps.resume_analyzer.models import ResumeAnalysis


# ==========================================================
# PROCESS RESUME
# ==========================================================

def process_resume(
    user,
    file_path: str
):
    """
    Process a resume and save the AI analysis.
    """

    # ------------------------------------------------------
    # Extract Resume Text
    # ------------------------------------------------------

    resume_text = extract_text(file_path)

    if not resume_text or not resume_text.strip():

        raise ValueError(
            "Resume contains no readable text."
        )

    resume_text = resume_text.strip()

    # ------------------------------------------------------
    # Parse Resume
    # ------------------------------------------------------
    #
    # Python extracts the candidate name and detects
    # sections such as:
    #
    # header
    # summary
    # education
    # experience
    # projects
    # skills
    # certifications
    # achievements
    #
    # We keep BOTH:
    #
    # 1. sections  -> structured information
    # 2. resume_text -> complete original text
    #
    # This gives Gemini better context for detailed reasoning.
    # ------------------------------------------------------

    candidate_name, sections = parse_resume(
        resume_text
    )

    # ------------------------------------------------------
    # ONE GEMINI CALL
    # ------------------------------------------------------
    #
    # Send:
    #
    # candidate_name
    # sections
    # complete resume text
    #
    # The complete text is important because section detection
    # may not perfectly understand every resume layout.
    # ------------------------------------------------------

    ai_result = analyze_resume(
        candidate_name,
        sections,
        resume_text
    )

    # ------------------------------------------------------
    # SAVE ANALYSIS
    # ------------------------------------------------------

    analysis = ResumeAnalysis.objects.create(

        user=user,

        ai_recommendations=ai_result

    )

    return analysis