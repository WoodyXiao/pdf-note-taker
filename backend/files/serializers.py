from rest_framework import serializers

from .models import PdfFile, Notebook


class PdfFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PdfFile
        fields = ["id", "file_id", "file_name", "file", "created_at"]
        read_only_fields = ["id", "file_id", "file", "created_at"]


class NotebookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notebook
        fields = ["id", "name", "created_at"]

