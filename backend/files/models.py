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

    def __str__(self):
        return self.file_name


class DocumentEmbedding(models.Model):
    """Stores vector embeddings for chunks of a PDF file."""

    file = models.ForeignKey(
        PdfFile, on_delete=models.CASCADE, related_name="embeddings"
    )
    text = models.TextField()
    embedding = VectorField(dimensions=768)
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


