import uuid

from django.conf import settings
from django.db import models
from pgvector.django import VectorField


class PdfFile(models.Model):
    file_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    file_name = models.CharField(max_length=255)
    file = models.FileField(upload_to="pdfs/")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pdf_files"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    # Whether the background embedding/ingest job has finished for this PDF.
    is_ingested = models.BooleanField(default=False)
    # Optional error message if ingest failed.
    ingest_error = models.TextField(null=True, blank=True)
    # Optional Celery task id for the ingest job (used for cancellation).
    ingest_task_id = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.file_name


class DocumentEmbedding(models.Model):
    """Stores vector embeddings for chunks of a PDF file."""

    file = models.ForeignKey(
        PdfFile, on_delete=models.CASCADE, related_name="embeddings"
    )
    text = models.TextField()
    embedding = VectorField(dimensions=768)
    # Optional page number within the source PDF (1-based indexing)
    page_number = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Embedding for {self.file.file_name}"


class Notebook(models.Model):
    """User-owned notebook that can group multiple PDF files."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notebooks"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.owner})"


class NotebookPage(models.Model):
    """A single page of rich-text content within a notebook.

    We start with a single page per notebook, but this structure is ready
    for future multi-page notebooks (ordered by order_index).
    """

    notebook = models.ForeignKey(
        Notebook, on_delete=models.CASCADE, related_name="pages"
    )
    title = models.CharField(max_length=255, blank=True)
    order_index = models.PositiveIntegerField(default=0)
    # Store the TipTap document as JSON for maximum flexibility.
    content = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order_index", "created_at"]

    def __str__(self):
        return f"Page {self.order_index} of {self.notebook}"


class NotebookPdf(models.Model):
    """Many-to-many relation between notebooks and PDF files."""

    notebook = models.ForeignKey(
        Notebook, on_delete=models.CASCADE, related_name="notebook_pdfs"
    )
    file = models.ForeignKey(
        PdfFile, on_delete=models.CASCADE, related_name="in_notebooks"
    )

    class Meta:
        unique_together = ("notebook", "file")


class ChatMessage(models.Model):
    """Persisted chat messages scoped to a notebook."""

    CHANNEL_NOTEBOOK_CHAT = "notebook_chat"
    CHANNEL_EDITOR_ASSIST = "editor_assist"

    notebook = models.ForeignKey(
        Notebook, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(
        max_length=10, choices=[("user", "User"), ("ai", "AI")]
    )
    channel = models.CharField(
        max_length=32,
        choices=[
            (CHANNEL_NOTEBOOK_CHAT, "Notebook Chat"),
            (CHANNEL_EDITOR_ASSIST, "Editor Assist"),
        ],
        default=CHANNEL_NOTEBOOK_CHAT,
    )
    # Store the rendered HTML we send to the frontend.
    content_html = models.TextField()
    # Optional metadata (selected text, source pages, etc.)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.notebook} [{self.channel}] {self.role}@{self.created_at}"


