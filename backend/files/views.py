from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from .models import PdfFile
from .serializers import PdfFileSerializer
from .tasks import ingest_pdf_task


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def upload_pdf(request):
    """Upload a PDF file, create a PdfFile record, and ingest it into the vector store."""
    user = request.user
    file_obj = request.FILES.get("file")
    file_name = request.data.get("fileName") or "Untitled File"

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


@api_view(["GET"])
def get_file(request, file_id):
    """Get metadata for a single PdfFile by file_id (UUID)."""
    pdf_file = get_object_or_404(PdfFile, file_id=file_id)
    serializer = PdfFileSerializer(pdf_file)
    data = serializer.data
    data["file_url"] = request.build_absolute_uri(pdf_file.file.url)
    return Response(data)



