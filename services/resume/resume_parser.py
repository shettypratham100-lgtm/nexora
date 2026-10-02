"""
==========================================================
Resume Parser
==========================================================

Responsible for preparing resume text for the AI Resume
Analyzer.

Responsibilities
----------------
• Extract candidate name
• Detect and group resume sections
• Preserve resume content

This module DOES NOT:
• Evaluate the resume
• Calculate scores
• Generate recommendations
• Build a candidate profile
"""

import re
from typing import Optional


# ==========================================================
# SECTION HEADINGS
# ==========================================================

SECTION_KEYWORDS = {

    "summary": [
        "summary",
        "professional summary",
        "profile",
        "profile summary",
        "career summary",
        "objective",
        "career objective",
        "professional objective",
    ],

    "education": [
        "education",
        "academic background",
        "academic qualifications",
        "educational background",
        "qualifications",
        "qualification",
    ],

    "experience": [
        "experience",
        "work experience",
        "professional experience",
        "employment history",
        "work history",
        "career history",
        "internship",
        "internships",
        "internship experience",
        "internship experiences",
        "industry experience",
    ],

    "projects": [
        "project",
        "projects",
        "academic project",
        "academic projects",
        "professional project",
        "professional projects",
        "key project",
        "key projects",
        "personal project",
        "personal projects",
        "technical project",
        "technical projects",
    ],

    "skills": [
        "skills",
        "technical skills",
        "technical expertise",
        "technical proficiencies",
        "technical competencies",
        "core competencies",
        "core skills",
        "professional skills",
        "key skills",
        "areas of expertise",
        "competencies",
        "technologies",
        "technical knowledge",
    ],

    "certifications": [
        "certification",
        "certifications",
        "certificate",
        "certificates",
        "license",
        "licenses",
        "licenses & certifications",
        "professional certifications",
    ],

    "achievements": [
        "achievement",
        "achievements",
        "accomplishment",
        "accomplishments",
        "award",
        "awards",
        "honor",
        "honors",
        "honour",
        "honours",
    ],

    "languages": [
        "language",
        "languages",
        "spoken languages",
        "language proficiency",
    ],

    "coursework": [
        "coursework",
        "relevant coursework",
        "academic coursework",
        "relevant courses",
        "courses",
    ],

    "publications": [
        "publication",
        "publications",
        "research publication",
        "research publications",
        "research papers",
        "papers",
    ],

    "volunteering": [
        "volunteering",
        "volunteer experience",
        "volunteer work",
        "community service",
    ],

    "extracurricular": [
        "extracurricular",
        "extracurricular activities",
        "activities",
        "co-curricular activities",
    ],

    "soft_skills": [
        "soft skills",
        "interpersonal skills",
        "professional strengths",
    ],
}


# ==========================================================
# NORMALIZE HEADING
# ==========================================================

def normalize_heading(line: str) -> str:
    """
    Normalize a possible resume section heading.

    Examples:
        Skills
        SKILLS
        Skills:
        Technical Skills:
    """

    line = line.strip().lower()

    # Remove common trailing heading characters.
    line = re.sub(r"[:\-|]+$", "", line)

    # Normalize whitespace.
    line = re.sub(r"\s+", " ", line)

    return line.strip()


# ==========================================================
# GET SECTION NAME
# ==========================================================

def get_section_name(line: str) -> Optional[str]:
    """
    Return the internal section name if the line matches
    a known resume section heading.
    """

    normalized = normalize_heading(line)

    for section_name, aliases in SECTION_KEYWORDS.items():

        if normalized in aliases:
            return section_name

    return None


# ==========================================================
# NAME EXTRACTION
# ==========================================================

def extract_name(text: str) -> Optional[str]:
    """
    Extract the likely candidate name from the beginning
    of the resume.

    This is only used for personalization/display.
    """

    cleaned_text = text

    # Remove email addresses.
    cleaned_text = re.sub(
        r"[A-Za-z0-9._%+-]+"
        r"@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        "",
        cleaned_text
    )

    # Remove Indian phone numbers.
    cleaned_text = re.sub(
        r"(?:\+91[\s\-]?)?[6-9]\d{9}",
        "",
        cleaned_text
    )

    # Remove URLs.
    cleaned_text = re.sub(
        r"(?:https?://|www\.)\S+",
        "",
        cleaned_text,
        flags=re.IGNORECASE
    )

    ignored_headings = {
        "resume",
        "curriculum vitae",
        "cv",
        "email",
        "phone",
        "contact",
        "linkedin",
        "github",
        "portfolio",
    }

    # Only inspect the first few lines.
    for line in cleaned_text.splitlines()[:10]:

        line = line.strip()

        if not line:
            continue

        normalized = normalize_heading(line)

        # Ignore generic labels.
        if normalized in ignored_headings:
            continue

        # Ignore recognized section headings.
        if get_section_name(line):
            continue

        # Names are usually short.
        if len(line.split()) > 5:
            continue

        return line

    return None


# ==========================================================
# SECTION DETECTION
# ==========================================================

def detect_sections(text: str) -> dict:
    """
    Detect and group major resume sections.

    The original content is preserved as much as possible.

    Example:

    {
        "header": "...",
        "summary": "...",
        "education": "...",
        "experience": "...",
        "projects": "...",
        "skills": "...",
        "certifications": "...",
        "achievements": "..."
    }
    """

    sections = {}

    current_section = "header"
    sections[current_section] = []

    for line in text.splitlines():

        clean_line = line.strip()

        if not clean_line:
            continue

        # Check whether this line is a section heading.
        section_name = get_section_name(clean_line)

        if section_name:

            current_section = section_name

            if current_section not in sections:
                sections[current_section] = []

            continue

        # Preserve resume content.
        sections[current_section].append(clean_line)

    # Convert lists into strings.
    cleaned_sections = {}

    for section_name, lines in sections.items():

        content = "\n".join(lines).strip()

        if content:
            cleaned_sections[section_name] = content

    return cleaned_sections


# ==========================================================
# MAIN PARSER
# ==========================================================

def parse_resume(
    resume_text: str
) -> tuple[Optional[str], dict]:
    """
    Prepare a resume for AI analysis.

    Returns:
        (
            candidate_name,
            sections
        )

    The parser only organizes the resume.
    It does not evaluate the candidate.
    """

    if not resume_text or not resume_text.strip():

        raise ValueError(
            "Resume text is empty."
        )

    candidate_name = extract_name(
        resume_text
    )

    sections = detect_sections(
        resume_text
    )

    if not sections:

        raise ValueError(
            "No resume content could be detected."
        )

    return candidate_name, sections