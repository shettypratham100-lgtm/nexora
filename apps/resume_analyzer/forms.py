"""
Resume Analyzer Forms
"""

from django import forms


class ResumeUploadForm(forms.Form):
    """
    Form used to upload a resume.

    The uploaded file is stored only temporarily.
    After analysis it is deleted automatically.
    """

    resume = forms.FileField(
        label="Upload Resume"
    )

    def clean_resume(self):

        file = self.cleaned_data["resume"]

        allowed_extensions = (
            ".pdf",
            ".docx"
        )

        filename = file.name.lower()

        if not filename.endswith(allowed_extensions):

            raise forms.ValidationError(
                "Only PDF and DOCX files are allowed."
            )

        # Maximum 10 MB
        max_size = 10 * 1024 * 1024

        if file.size > max_size:

            raise forms.ValidationError(
                "Resume size must be below 10 MB."
            )

        return file