from django.urls import path

from . import views

urlpatterns = [
    # PDF files
    path("", views.list_files, name="list_files"),
    path("upload/", views.upload_pdf, name="upload_pdf"),
    path("<uuid:file_id>/", views.get_file, name="get_file"),
    # Notebooks
    path("notebooks/", views.notebooks, name="notebooks"),
    path(
        "notebooks/<uuid:notebook_id>/files/",
        views.notebook_files,
        name="notebook_files",
    ),
    path(
        "notebooks/<uuid:notebook_id>/",
        views.notebook_detail,
        name="notebook_detail",
    ),
]


