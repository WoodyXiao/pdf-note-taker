import json
import os

import redis
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from celery import current_app as celery_app

from .models import ChatMessage, Notebook, NotebookPage, NotebookPdf, PdfFile
from .serializers import (
    ChatMessageSerializer,
    NotebookContentSerializer,
    NotebookPageSerializer,
    NotebookSerializer,
    PdfFileSerializer,
)
from .tasks import ingest_pdf_task


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def upload_pdf(request):
    """Upload a PDF file, create a PdfFile record, and ingest it into the vector store."""
    user = request.user
    file_obj = request.FILES.get("file")
    # Default file name to uploaded file's original name if none provided
    file_name = request.data.get("fileName") or getattr(file_obj, "name", None) or "Untitled File"

    if not file_obj:
        return Response(
            {"detail": "No file provided"}, status=status.HTTP_400_BAD_REQUEST
        )

    pdf_file = PdfFile.objects.create(
        file=file_obj,
        file_name=file_name,
        created_by=user,
    )

    # Ingest PDF into vector store asynchronously via Celery
    async_result = ingest_pdf_task.delay(pdf_file.id)
    # Remember the task id so we can cancel it if the PDF is deleted.
    pdf_file.ingest_task_id = async_result.id
    pdf_file.save(update_fields=["ingest_task_id"])

    serializer = PdfFileSerializer(pdf_file)
    data = serializer.data
    # Ensure frontend gets an absolute URL to embed in an iframe
    data["file_url"] = request.build_absolute_uri(pdf_file.file.url)
    return Response(data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def list_files(request):
    """List all PDF files created by the current user."""
    user = request.user
    qs = PdfFile.objects.filter(created_by=user).order_by("-created_at")
    serializer = PdfFileSerializer(qs, many=True)
    data = serializer.data
    # Attach absolute URLs for each file
    for item, obj in zip(data, qs):
        item["file_url"] = request.build_absolute_uri(obj.file.url)
    return Response(data)


@api_view(["GET", "DELETE"])
def get_file(request, file_id):
    """
    GET: Get metadata for a single PdfFile by file_id (UUID).
    DELETE: Remove the PdfFile and its related embeddings/notebook links.
    """
    pdf_file = get_object_or_404(PdfFile, file_id=file_id, created_by=request.user)

    if request.method == "DELETE":
        # Best-effort: cancel any running ingest task for this file.
        if pdf_file.ingest_task_id:
            try:
                celery_app.control.revoke(pdf_file.ingest_task_id, terminate=True)
            except Exception:
                # Cancellation is best-effort only; deletion should still proceed.
                pass
        pdf_file.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = PdfFileSerializer(pdf_file)
    data = serializer.data
    data["file_url"] = request.build_absolute_uri(pdf_file.file.url)
    return Response(data)


@api_view(["GET", "POST"])
def notebooks(request):
    """
    GET: List all notebooks for current user.
    POST: Create a new notebook with given name.
    """
    user = request.user

    if request.method == "GET":
        qs = Notebook.objects.filter(owner=user).order_by("-created_at")
        serializer = NotebookSerializer(qs, many=True)
        return Response(serializer.data)

    # POST
    name = request.data.get("name") or "Untitled Notebook"
    notebook = Notebook.objects.create(owner=user, name=name)
    serializer = NotebookSerializer(notebook)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "DELETE"])
def notebook_detail(request, notebook_id):
    """
    Get a single notebook (id, name, created_at).
    """
    notebook = get_object_or_404(Notebook, id=notebook_id, owner=request.user)

    if request.method == "DELETE":
        notebook.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = NotebookSerializer(notebook)
    return Response(serializer.data)


@api_view(["GET", "PUT"])
def notebook_files(request, notebook_id):
    """
    GET: Return list of fileIds attached to the notebook.
    PUT: Replace notebook's file set with provided fileIds.
    """
    notebook = get_object_or_404(Notebook, id=notebook_id, owner=request.user)

    if request.method == "GET":
        file_ids = list(
            NotebookPdf.objects.filter(notebook=notebook).values_list(
                "file__file_id", flat=True
            )
        )
        return Response({"fileIds": file_ids})

    # PUT: update selection
    ids = request.data.get("fileIds") or []
    # Map external file_id (UUID) to PdfFile objects for this user
    pdfs = list(
        PdfFile.objects.filter(
            file_id__in=ids, created_by=request.user
        )
    )

    NotebookPdf.objects.filter(notebook=notebook).delete()
    NotebookPdf.objects.bulk_create(
        [NotebookPdf(notebook=notebook, file=pdf) for pdf in pdfs]
    )

    return Response({"fileIds": ids}, status=status.HTTP_200_OK)


@api_view(["GET", "PUT"])
def notebook_content(request, notebook_id):
    """
    GET: Return notebook pages (currently we use a single page with index 0).
    PUT: Upsert the primary page content.
    """
    notebook = get_object_or_404(Notebook, id=notebook_id, owner=request.user)

    if request.method == "GET":
        pages = list(
            NotebookPage.objects.filter(notebook=notebook).order_by(
                "order_index", "created_at"
            )
        )
        if not pages:
            # Lazily create an empty main page so frontend always sees one.
            page = NotebookPage.objects.create(
                notebook=notebook, title="Main", order_index=0, content={}
            )
            pages = [page]

        serializer = NotebookPageSerializer(pages, many=True)
        return Response({"pages": serializer.data})

    # PUT: update primary page (index 0) for now.
    pages_data = request.data.get("pages", [])
    if not pages_data:
        return Response(
            {"detail": "pages is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    first_page = pages_data[0]
    title = first_page.get("title") or "Main"
    content = first_page.get("content") or {}

    page, _created = NotebookPage.objects.get_or_create(
        notebook=notebook,
        order_index=0,
        defaults={"title": title, "content": content},
    )
    if not _created:
        page.title = title
        page.content = content
        page.save(update_fields=["title", "content", "updated_at"])

    serializer = NotebookPageSerializer(page)
    return Response({"pages": [serializer.data]})


@api_view(["GET", "POST"])
def notebook_messages(request, notebook_id):
    """
    GET: Return recent chat messages for a notebook.
    POST: Create a new chat message (typically a user message).
    """
    notebook = get_object_or_404(Notebook, id=notebook_id, owner=request.user)

    if request.method == "GET":
        channel = request.query_params.get("channel")
        limit = int(request.query_params.get("limit", "50"))

        qs = ChatMessage.objects.filter(notebook=notebook)
        if channel:
            qs = qs.filter(channel=channel)

        # Newest first, then reversed so frontend gets chronological order.
        qs = list(qs.order_by("-created_at")[:limit])
        qs.reverse()

        serializer = ChatMessageSerializer(qs, many=True)
        return Response(serializer.data)

    # POST: create a message (usually role=user).
    role = request.data.get("role")
    content_html = request.data.get("contentHtml")
    channel = request.data.get("channel") or ChatMessage.CHANNEL_NOTEBOOK_CHAT
    metadata = request.data.get("metadata") or None

    if role not in ("user", "ai"):
        return Response(
            {"detail": "role must be 'user' or 'ai'"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not content_html:
        return Response(
            {"detail": "contentHtml is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    msg = ChatMessage.objects.create(
        notebook=notebook,
        role=role,
        channel=channel,
        content_html=content_html,
        metadata=metadata,
    )
    serializer = ChatMessageSerializer(msg)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


def ingest_events(request):
    """
    Server-Sent Events stream for PDF ingest status updates.

    Each event's data is a JSON object:
    {
      "type": "pdf_ingested",
      "file_id": "<uuid>",
      "is_ingested": true/false,
      "ingest_error": "... or null ..."
    }
    """

    def event_stream():
        redis_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url)
        pubsub = r.pubsub()
        pubsub.subscribe("pdf_ingest_events")

        # Initial comment to establish the stream.
        yield ": connected to pdf_ingest_events\n\n"

        try:
            for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")

                # Basic validation: ensure it's valid JSON; otherwise skip.
                try:
                    json.loads(data)
                except Exception:
                    continue

                yield f"data: {data}\n\n"
        finally:
            pubsub.close()

    if request.method != "GET":
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    return response

