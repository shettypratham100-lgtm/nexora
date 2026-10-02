from django.urls import path

from . import views

app_name = "document_toolkit"

urlpatterns = [

    path("", views.toolkit_home, name="home"),

    path("create-pdf/", views.create_pdf, name="create_pdf"),
    path("merge/", views.merge_pdf, name="merge_pdf"),
    path("split/", views.split_pdf, name="split_pdf"),
    path("compress/", views.compress_pdf, name="compress_pdf"),
    path("page-numbers/", views.page_numbers, name="page_numbers"),
    path("watermark/", views.watermark_pdf, name="watermark_pdf"),
    path("rotate/", views.rotate_pdf, name="rotate_pdf"),
    path("pdf-to-docx/", views.pdf_to_docx, name="pdf_to_docx"),
    path("docx-to-pdf/", views.docx_to_pdf, name="docx_to_pdf"),
    path("ppt-to-pdf/", views.ppt_to_pdf, name="ppt_to_pdf"),
    path("image-to-pdf/", views.image_to_pdf, name="image_to_pdf"),

    path("jobs/<int:pk>/delete/", views.delete_job, name="delete_job"),
]
