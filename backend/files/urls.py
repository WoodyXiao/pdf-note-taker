from django.urls import path

from . import views

urlpatterns = [
    path("", views.list_files, name="list_files"),
    path("upload/", views.upload_pdf, name="upload_pdf"),
    path("<uuid:file_id>/", views.get_file, name="get_file"),
]


