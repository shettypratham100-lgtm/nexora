from django import forms


# ============================================================
# CREATE PDF (FROM TEXT)
# ============================================================

class CreatePdfForm(forms.Form):

    title = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Title (optional)",
        }),
    )

    body_text = forms.CharField(
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 12,
            "placeholder": "Type or paste your notes here...",
        }),
    )


# ============================================================
# MERGE PDF
#
# Files themselves are read via request.FILES.getlist("files")
# in the view, since Django's plain FileField only accepts one
# file per field.
# ============================================================

class MergePdfForm(forms.Form):
    pass


# ============================================================
# SPLIT PDF
# ============================================================

SPLIT_MODE_CHOICES = [
    ("range", "Extract a page range"),
    ("all", "Split into individual pages (ZIP)"),
]


class SplitPdfForm(forms.Form):

    mode = forms.ChoiceField(
        choices=SPLIT_MODE_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    start_page = forms.IntegerField(
        min_value=1,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "e.g. 1"}),
    )

    end_page = forms.IntegerField(
        min_value=1,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "e.g. 5"}),
    )

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get("mode") == "range":

            if not cleaned_data.get("start_page") or not cleaned_data.get("end_page"):
                raise forms.ValidationError(
                    "Enter both a start page and an end page."
                )

        return cleaned_data


# ============================================================
# COMPRESS PDF
# ============================================================

COMPRESSION_CHOICES = [
    ("low", "Maximum compression (lower image quality)"),
    ("medium", "Balanced (recommended)"),
    ("high", "Light compression (best quality)"),
]


class CompressPdfForm(forms.Form):

    image_quality = forms.ChoiceField(
        choices=COMPRESSION_CHOICES,
        initial="medium",
        widget=forms.Select(attrs={"class": "form-select"}),
    )


# ============================================================
# ADD PAGE NUMBERS
# ============================================================

VERTICAL_POSITION_CHOICES = [
    ("bottom", "Bottom"),
    ("top", "Top"),
]

ALIGNMENT_CHOICES = [
    ("left", "Left"),
    ("center", "Center"),
    ("right", "Right"),
]

NUMBER_FORMAT_CHOICES = [
    ("plain", "1"),
    ("page", "Page 1"),
    ("page_of", "Page 1 of 10"),
]


class PageNumbersForm(forms.Form):

    vertical_position = forms.ChoiceField(
        choices=VERTICAL_POSITION_CHOICES,
        initial="bottom",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    alignment = forms.ChoiceField(
        choices=ALIGNMENT_CHOICES,
        initial="center",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    number_format = forms.ChoiceField(
        choices=NUMBER_FORMAT_CHOICES,
        initial="page_of",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    start_at = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    font_size = forms.IntegerField(
        min_value=6,
        max_value=48,
        initial=10,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )


# ============================================================
# WATERMARK PDF
# ============================================================

class WatermarkPdfForm(forms.Form):

    watermark_text = forms.CharField(
        max_length=80,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g. CONFIDENTIAL, your name, draft copy...",
        }),
    )


# ============================================================
# ROTATE PDF
# ============================================================

ROTATE_CHOICES = [
    (90, "Rotate 90° clockwise"),
    (180, "Rotate 180°"),
    (270, "Rotate 270° clockwise"),
]


class RotatePdfForm(forms.Form):

    angle = forms.TypedChoiceField(
        choices=ROTATE_CHOICES,
        coerce=int,
        widget=forms.Select(attrs={"class": "form-select"}),
    )


# ============================================================
# CONVERT: OFFICE -> PDF / PDF -> DOCX / IMAGES -> PDF
#
# These tools are just "upload file(s), click go" -- no extra
# fields needed beyond the file input itself.
# ============================================================

class SingleFileForm(forms.Form):
    pass
