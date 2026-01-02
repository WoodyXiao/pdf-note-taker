import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from pgvector.django import VectorField


class PdfFile(models.Model):
    file_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    file_name = models.CharField(max_length=255)
    file = models.FileField(upload_to="pdfs/")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pdf_files"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    # Content fingerprint used for per-user dedup. SHA-256 hex string.
    # Nullable for backwards compatibility with existing DBs/branches.
    content_sha256 = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    # Optional file size (helps debugging/UX)
    size_bytes = models.BigIntegerField(null=True, blank=True)
    # Whether the background embedding/ingest job has finished for this PDF.
    is_ingested = models.BooleanField(default=False)
    # Optional error message if ingest failed.
    ingest_error = models.TextField(null=True, blank=True)
    # Optional Celery task id for the ingest job (used for cancellation).
    ingest_task_id = models.CharField(max_length=255, null=True, blank=True)

    # C3: richer ingest state (keeps backwards compatibility with is_ingested/ingest_error)
    INGEST_PENDING = "pending"
    INGEST_RUNNING = "running"
    INGEST_SUCCEEDED = "succeeded"
    INGEST_FAILED = "failed"
    INGEST_CANCELLED = "cancelled"
    INGEST_STATUS_CHOICES = [
        (INGEST_PENDING, "Pending"),
        (INGEST_RUNNING, "Running"),
        (INGEST_SUCCEEDED, "Succeeded"),
        (INGEST_FAILED, "Failed"),
        (INGEST_CANCELLED, "Cancelled"),
    ]

    ingest_status = models.CharField(
        max_length=16, choices=INGEST_STATUS_CHOICES, default=INGEST_PENDING
    )
    ingest_progress = models.PositiveSmallIntegerField(default=0)  # 0..100
    ingest_total_chunks = models.IntegerField(null=True, blank=True)
    ingest_done_chunks = models.IntegerField(null=True, blank=True)
    ingest_started_at = models.DateTimeField(null=True, blank=True)
    ingest_finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            # Avoid duplicate uploads for the same user and the same content.
            # Keep nullable rows allowed; only enforce when content_sha256 is present.
            models.UniqueConstraint(
                fields=["created_by", "content_sha256"],
                condition=Q(content_sha256__isnull=False) & ~Q(content_sha256=""),
                name="uniq_user_content_sha256",
            )
        ]

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


class ActivityLog(models.Model):
    """Simple user-scoped activity log for auditing and timeline views."""

    ACTION_UPLOAD_PDF = "upload_pdf"
    ACTION_DELETE_PDF = "delete_pdf"
    ACTION_REINGEST_PDF = "reingest_pdf"
    ACTION_CREATE_NOTEBOOK = "create_notebook"
    ACTION_DELETE_NOTEBOOK = "delete_notebook"
    ACTION_LOGIN = "login"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="activities",
    )
    action_type = models.CharField(max_length=64)

    # Generic target reference for display / filtering.
    target_type = models.CharField(max_length=64, blank=True)
    target_id = models.CharField(max_length=64, blank=True)
    target_name = models.CharField(max_length=255, blank=True)

    # Extra structured data (e.g. file size, notebook id, ip, etc.)
    metadata = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["user", "action_type"]),
        ]

    def __str__(self):
        return f"{self.user} {self.action_type} {self.target_name} @ {self.created_at}"


