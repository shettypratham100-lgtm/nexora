"""
AI Service

Responsible for communicating with Gemini AI.

Responsibilities
----------------
- Send extracted document text to Gemini.
- Generate an AI summary.
- Extract document keywords.
- Parse and validate the JSON response.

Not Responsible For
-------------------
- Database updates
- Retry logic
- Resource management
"""

import json

import google.generativeai as genai

from django.conf import settings


from services.ai.prompts import (
    RESOURCE_ANALYZER_PROMPT,
    build_resume_report_prompt,
)


# Configure Gemini using the API key from Django settings.
genai.configure(api_key=settings.GEMINI_API_KEY)

# Configure Gemini to always return JSON.
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config={
        "response_mime_type": "application/json",
    },
)


def analyze_document(text):
    """
    Generate an AI summary and keywords for the extracted document text.

    Parameters
    ----------
    text : str
        Plain text extracted from the uploaded document.

    Returns
    -------
    dict
        Example:
        {
            "summary": "...",
            "keywords": [
                "...",
                "..."
            ]
        }

    Raises
    ------
    ValueError
        If the extracted text is empty or the AI response is invalid.

    RuntimeError
        If Gemini fails to process the document.
    """

    # Remove leading and trailing whitespace.
    text = text.strip()

    # Prevent sending empty documents to Gemini.
    if not text:
        raise ValueError("Document contains no extractable text.")

    # Limit the amount of text sent to Gemini.
    MAX_CHARACTERS = 50000

    if len(text) > MAX_CHARACTERS:
        text = text[:MAX_CHARACTERS]

    # Combine prompt and document text.
    prompt = f"{RESOURCE_ANALYZER_PROMPT}\n\n{text}"

    try:
        # Generate AI response.
        response = model.generate_content(prompt)

        # Convert JSON response into a Python dictionary.
        result = json.loads(response.text)

        # ----------------------------------------------------------
        # Validate summary
        # ----------------------------------------------------------
        summary = result.get("summary")

        if not isinstance(summary, str):
            raise ValueError("AI response contains an invalid summary.")

        summary = summary.strip()

        if not summary:
            raise ValueError("AI response returned an empty summary.")

        # ----------------------------------------------------------
        # Validate keywords
        # ----------------------------------------------------------
        keywords = result.get("keywords")

        if not isinstance(keywords, list):
            raise ValueError("AI response contains invalid keywords.")

        validated_keywords = []
        seen = set()

        document_text = text.lower()

        for keyword in keywords:

            if not isinstance(keyword, str):
                continue

            keyword = keyword.strip()

            if not keyword:
                continue

            # Only keep keywords that actually exist in the document.
            if keyword.lower() not in document_text:
                continue

            # Remove duplicates.
            normalized = keyword.lower()

            if normalized in seen:
                continue

            seen.add(normalized)

            validated_keywords.append(keyword)

        return {
            "summary": summary,
            "keywords": validated_keywords,
        }

    except json.JSONDecodeError as e:
        raise RuntimeError(
            "Failed to parse Gemini JSON response."
        ) from e

    except Exception as e:
        raise RuntimeError(
            f"Gemini analysis failed: {str(e)}"
        ) from e

# ==========================================================
# INTERNAL JSON GENERATOR
# ==========================================================

def _generate_json_response(prompt: str) -> dict:
    """
    Send a prompt to Gemini and return parsed JSON.
    """

    try:

        response = model.generate_content(prompt)

        return json.loads(response.text)

    except json.JSONDecodeError as e:

        raise RuntimeError(
            "Gemini returned invalid JSON."
        ) from e

    except Exception as e:

        raise RuntimeError(
            f"Gemini request failed: {str(e)}"
        ) from e


# ==========================================================
# RESUME ANALYZER
# ==========================================================

def analyze_resume(
    candidate_name: str,
    sections: dict,
    resume_text: str
) -> dict:
    """
    Analyze a resume using ONE Gemini call.

    Parameters
    ----------
    candidate_name : str
        Candidate name extracted by Python.

    sections : dict
        Resume sections detected by the resume parser.

    resume_text : str
        Complete extracted resume text.

    Returns
    -------
    dict
        AI-generated Resume Intelligence Report.
    """

    # ------------------------------------------------------
    # Validate Candidate Name
    # ------------------------------------------------------

    if not isinstance(candidate_name, str):

        candidate_name = ""

    candidate_name = candidate_name.strip()


    # ------------------------------------------------------
    # Validate Resume Sections
    # ------------------------------------------------------

    if not isinstance(sections, dict):

        raise ValueError(
            "Resume sections must be a dictionary."
        )

    if not sections:

        raise ValueError(
            "No resume sections were detected."
        )


    # ------------------------------------------------------
    # Validate Original Resume Text
    # ------------------------------------------------------

    if not isinstance(resume_text, str):

        raise ValueError(
            "Resume text must be a string."
        )

    resume_text = resume_text.strip()

    if not resume_text:

        raise ValueError(
            "Resume text is empty."
        )


    # ------------------------------------------------------
    # Build Prompt
    # ------------------------------------------------------

    prompt = build_resume_report_prompt(
        candidate_name,
        sections,
        resume_text
    )


    # ------------------------------------------------------
    # ONE GEMINI CALL
    # ------------------------------------------------------

    result = _generate_json_response(
        prompt
    )


    # ------------------------------------------------------
    # Validate Required Fields
    # ------------------------------------------------------

    required_fields = (

        "overall_resume_score",

        "ats_score",

        "strengths",

        "areas_to_improve",

        "resume_improvements",

    )

    for field in required_fields:

        if field not in result:

            raise RuntimeError(
                f"Gemini response is missing '{field}'."
            )


    # ------------------------------------------------------
    # Validate Scores
    # ------------------------------------------------------

    for score_field in (

        "overall_resume_score",

        "ats_score",

    ):

        score_data = result[score_field]

        if not isinstance(
            score_data,
            dict
        ):

            raise RuntimeError(
                f"Invalid {score_field} structure."
            )


        score = score_data.get(
            "score"
        )

        if not isinstance(
            score,
            (int, float)
        ):

            raise RuntimeError(
                f"Invalid {score_field} score."
            )


        if not 0 <= score <= 100:

            raise RuntimeError(
                f"{score_field} must be between 0 and 100."
            )


        reason = score_data.get(
            "reason"
        )

        if not isinstance(
            reason,
            str
        ):

            raise RuntimeError(
                f"Invalid {score_field} reason."
            )


    # ------------------------------------------------------
    # Validate Lists
    # ------------------------------------------------------

    list_fields = (

        "strengths",

        "areas_to_improve",

        "resume_improvements",

    )

    for field in list_fields:

        if not isinstance(
            result[field],
            list
        ):

            raise RuntimeError(
                f"Invalid {field} format."
            )


    return result