import os

from django.shortcuts import get_object_or_404
from pgvector.django import CosineDistance
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from files.models import DocumentEmbedding, Notebook, NotebookPdf, PdfFile


@api_view(["POST"])
def answer(request):
    """
    End-to-end RAG endpoint:
    - Embed the question
    - Retrieve top-k relevant chunks for the given fileId
    - Ask Gemini to answer in HTML
    - Return the HTML back to the frontend
    """
    question = request.data.get("question", "").strip()
    notebook_id = request.data.get("notebookId")
    file_id = request.data.get("fileId")  # legacy support

    if not question:
        return Response(
            {"detail": "question is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    api_key = os.getenv("NEXT_PUBLIC_GEMINI_API_KEY")
    if not api_key:
        return Response(
            {"detail": "NEXT_PUBLIC_GEMINI_API_KEY environment variable is not set"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # 1. Embed the question
    embeddings_model = GoogleGenerativeAIEmbeddings(
        model="text-embedding-004",
        google_api_key=api_key,
    )
    query_vector = embeddings_model.embed_query(question)

    # 2. Determine which PDF files to search over
    files_qs = None

    if notebook_id:
        # New behavior: use all files attached to the given notebook that belong to the user.
        notebook = get_object_or_404(
            Notebook, id=notebook_id, owner=request.user
        )
        file_ids = NotebookPdf.objects.filter(notebook=notebook).values_list(
            "file_id", flat=True
        )
        files_qs = PdfFile.objects.filter(id__in=file_ids, created_by=request.user)

        if not files_qs.exists():
            return Response(
                {"detail": "No PDFs selected in this notebook."},
                status=status.HTTP_400_BAD_REQUEST,
            )
    elif file_id:
        # Legacy behavior: single file context
        pdf_file = get_object_or_404(PdfFile, file_id=file_id)
        files_qs = PdfFile.objects.filter(id=pdf_file.id, created_by=request.user)
    else:
        return Response(
            {"detail": "Either notebookId or fileId is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 3. Retrieve top-k similar chunks across the selected files
    candidates = (
        DocumentEmbedding.objects.filter(file__in=files_qs)
        .annotate(distance=CosineDistance("embedding", query_vector))
        .order_by("distance")[:10]
    )

    all_unformatted_answer = "".join([c.text for c in candidates])

    # 3. Ask Gemini to answer in HTML format
    # Prefer model from environment (configured in Google AI Studio), fallback to gemini-flash-latest.
    model_id = os.getenv("GEMINI_CHAT_MODEL", "gemini-flash-latest")

    llm = ChatGoogleGenerativeAI(
        model=model_id,
        temperature=1,
        max_output_tokens=8192,
        google_api_key=api_key,
    )

    prompt = (
        f"For question : {question} and with the given content as answer, "
        f"please give appropriate answer in HTML format. "
        f'The answer content is {all_unformatted_answer}'
    )

    result = llm.invoke(prompt)
    raw_text = str(getattr(result, "content", result))

    # 4. Lightly clean markdown code fencing if present
    cleaned = (
        raw_text.replace("```", "")
        .replace("html", "")
        .replace("HTML", "")
        .strip()
    )

    return Response({"html": cleaned})


