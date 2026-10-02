from django.db import models
from django.conf import settings


# ==========================================================
# RESUME ANALYSIS
# ==========================================================

class ResumeAnalysis(models.Model):

    # ------------------------------------------------------
    # Owner of this analysis
    # ------------------------------------------------------

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="resume_analyses"
    )

    # ------------------------------------------------------
    # AI-generated resume analysis
    #
    # Contains:
    # - Overall Resume Score
    # - ATS Score
    # - Strengths
    # - Areas to Improve
    # - Improvements
    # ------------------------------------------------------

    ai_recommendations = models.JSONField()

    # ------------------------------------------------------
    # Analysis Timestamp
    # ------------------------------------------------------

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = ["-created_at"]

        verbose_name = "Resume Analysis"

        verbose_name_plural = "Resume Analyses"

    def __str__(self):

        return (
            f"{self.user.username} "
            f"- Resume Analysis "
            f"({self.created_at:%d %b %Y})"
        )