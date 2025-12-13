from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from .models import Notebook, NotebookPdf, PdfFile
from .serializers import NotebookSerializer, PdfFileSerializer
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
    ingest_pdf_task.delay(pdf_file.id)

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

