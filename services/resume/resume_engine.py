"""
==========================================================
Resume Engine
==========================================================

Builds objective resume evidence.

This module DOES NOT:

• Call Gemini
• Calculate AI scores
• Generate recommendations

Its responsibility is to prepare measurable facts
about the resume for Nexora's AI.
"""

from services.resume.resume_parser import CandidateProfile

# ==========================================================
# SECTION ANALYSIS
# ==========================================================

def analyze_sections(profile: CandidateProfile):
    """
    Analyze which resume sections are present.

    Returns
    -------
    dict
    """

    return {

        "summary": {

            "present": bool(profile.summary.strip())

        },

        "education": {

            "present": len(profile.education) > 0,

            "count": len(profile.education)

        },

        "experience": {

            "present": len(profile.experience) > 0,

            "count": len(profile.experience)

        },

        "projects": {

            "present": len(profile.projects) > 0,

            "count": len(profile.projects)

        },

        "technical_skills": {

            "present": len(profile.technical_skills) > 0,

            "count": len(profile.technical_skills)

        },

        "soft_skills": {

            "present": len(profile.soft_skills) > 0,

            "count": len(profile.soft_skills)

        },

        "tools": {

            "present": len(profile.tools) > 0,

            "count": len(profile.tools)

        },

        "certifications": {

            "present": len(profile.certifications) > 0,

            "count": len(profile.certifications)

        },

        "languages": {

            "present": len(profile.languages) > 0,

            "count": len(profile.languages)

        }

    }

# ==========================================================
# CONTACT ANALYSIS
# ==========================================================

def analyze_contact(profile: CandidateProfile):
    """
    Analyze available contact information.
    """

    contact = profile.contact

    return {

        "name": bool(contact.name),

        "email": bool(contact.email),

        "phone": bool(contact.phone),

        "linkedin": bool(contact.linkedin),

        "github": bool(contact.github),

        "portfolio": bool(contact.portfolio),

        "location": bool(contact.location)

    }

# ==========================================================
# RESUME STATISTICS
# ==========================================================

def build_statistics(profile: CandidateProfile):
    """
    Build useful statistics from the resume.

    Returns
    -------
    dict
    """

    project_technologies = set()

    for project in profile.projects:

        for technology in project.technologies:

            technology = technology.strip()

            if technology:

                project_technologies.add(
                    technology
                )

    return {

        "education_count": len(profile.education),

        "experience_count": len(profile.experience),

        "project_count": len(profile.projects),

        "technical_skill_count": len(
            profile.technical_skills
        ),

        "soft_skill_count": len(
            profile.soft_skills
        ),

        "tool_count": len(
            profile.tools
        ),

        "certification_count": len(
            profile.certifications
        ),

        "language_count": len(
            profile.languages
        ),

        "project_technologies": sorted(
            project_technologies
        )

    }

# ==========================================================
# ATS CHECKS
# ==========================================================

def build_ats_checks(profile: CandidateProfile):
    """
    Build ATS-related resume checks.

    Returns
    -------
    dict
    """

    contact = profile.contact

    return {

        "has_name": bool(contact.name),

        "has_email": bool(contact.email),

        "has_phone": bool(contact.phone),

        "has_summary": bool(profile.summary.strip()),

        "has_education": len(profile.education) > 0,

        "has_experience": len(profile.experience) > 0,

        "has_projects": len(profile.projects) > 0,

        "has_technical_skills": len(
            profile.technical_skills
        ) > 0,

        "has_certifications": len(
            profile.certifications
        ) > 0,

        "has_languages": len(
            profile.languages
        ) > 0

    }

# ==========================================================
# BUILD RESUME EVIDENCE
# ==========================================================

def build_resume_evidence(profile: CandidateProfile):
    """
    Build the complete resume evidence.

    This evidence is used by:

    • Career Matcher
    • Gemini
    • Dashboard

    Returns
    -------
    dict
    """

    return {

        "sections": analyze_sections(
            profile
        ),

        "contact": analyze_contact(
            profile
        ),

        "statistics": build_statistics(
            profile
        ),

        "ats_checks": build_ats_checks(
            profile
        )

    }