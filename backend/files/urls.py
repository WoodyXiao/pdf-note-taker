from django.urls import path

from . import views

urlpatterns = [
    # PDF files
    path("", views.list_files, name="list_files"),
    path("upload/", views.upload_pdf, name="upload_pdf"),
    path("events/", views.ingest_events, name="ingest_events"),
    path("<uuid:file_id>/reingest/", views.reingest_file, name="reingest_file"),
    path("<uuid:file_id>/", views.get_file, name="get_file"),
    path("activity/", views.activity_list, name="activity_list"),
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
    path(
        "notebooks/<uuid:notebook_id>/content/",
        views.notebook_content,
        name="notebook_content",
    ),
    path(
        "notebooks/<uuid:notebook_id>/messages/",
        views.notebook_messages,
        name="notebook_messages",
    ),
]


