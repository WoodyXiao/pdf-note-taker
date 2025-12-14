from rest_framework import serializers

from .models import ActivityLog, ChatMessage, Notebook, NotebookPage, PdfFile


class PdfFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PdfFile
        fields = [
            "id",
            "file_id",
            "file_name",
            "file",
            "created_at",
            "is_ingested",
            "ingest_error",
        ]
        read_only_fields = [
            "id",
            "file_id",
            "file",
            "created_at",
            "is_ingested",
            "ingest_error",
        ]


class NotebookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notebook
        fields = ["id", "name", "created_at"]


class NotebookPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotebookPage
        fields = ["id", "title", "order_index", "content", "created_at", "updated_at"]


class NotebookContentSerializer(serializers.Serializer):
    """Wrapper serializer for notebook content API: list of pages."""

    pages = NotebookPageSerializer(many=True)


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "role",
            "channel",
            "content_html",
            "metadata",
            "created_at",
        ]


class ActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityLog
        fields = [
            "id",
            "action_type",
            "target_type",
            "target_id",
            "target_name",
            "metadata",
            "created_at",
        ]

