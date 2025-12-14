import os
import re
from collections import defaultdict

from django.shortcuts import get_object_or_404
from pgvector.django import CosineDistance
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from files.models import ChatMessage, DocumentEmbedding, Notebook, NotebookPdf, PdfFile


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
    channel = request.data.get("channel") or ChatMessage.CHANNEL_NOTEBOOK_CHAT
    selected_text = request.data.get("selectedText")
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

    notebook = None

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
        temperature=0.7,
        max_output_tokens=8192,
        google_api_key=api_key,
    )

    prompt = (
        "You are an assistant helping a user study their PDF notes.\n"
        "Using ONLY the provided context, answer the user's question in clear HTML.\n"
        "Rules:\n"
        "- Return ONLY an HTML fragment (no <html>, <head>, or <body> tags).\n"
        "- Use simple tags like <p>, <h2>, <h3>, <ul>, <ol>, <li>, <strong>, <em>, <code>.\n"
        "- Do NOT include language attributes like lang=\"en\".\n"
        "- Avoid LaTeX or TeX syntax such as $, $$, \\(, \\); instead, write formulas in plain text, "
        'for example: "x^2 + y^2 = 1" or "1/2".\n'
        "- Provide a well-structured, reasonably detailed explanation with headings and bullet points when helpful.\n\n"
        f"User question:\n{question}\n\n"
        "Relevant context from the PDFs:\n"
        f"{all_unformatted_answer}\n"
    )

    result = llm.invoke(prompt)

    # Gemini responses can be either a plain string or a list of content parts.
    content = getattr(result, "content", result)

    if isinstance(content, str):
        raw_text = content
    elif isinstance(content, list):
        # Extract "text" fields from structured content parts
        parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                parts.append(part.get("text", ""))
            else:
                parts.append(str(part))
        raw_text = "\n".join(parts)
    else:
        raw_text = str(content)

    # 4. Lightly clean markdown/code fencing and strip outer html/body tags if any
    no_fences = raw_text.replace("```", "").strip()
    # Remove <html>, </html>, <body>, </body> if model still returns them
    cleaned = re.sub(
        r"</?(html|body)[^>]*>",
        "",
        no_fences,
        flags=re.IGNORECASE,
    ).strip()

    # Additional light LaTeX cleanup: keep the text but drop common TeX markers
    # Remove inline/blocked $...$ while keeping the inner content
    cleaned = re.sub(r"\$\$(.+?)\$\$", r"\1", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"\$(.+?)\$", r"\1", cleaned, flags=re.DOTALL)
    # \text{...} -> ...
    cleaned = re.sub(r"\\text\{([^}]*)\}", r"\1", cleaned)
    # Replace some common greek letters to plain text names
    cleaned = re.sub(
        r"\\(alpha|beta|gamma|delta|theta|lambda|rho|sigma|mu|nu|pi|phi|psi|omega)\b",
        r"\1",
        cleaned,
    )
    # Drop any remaining backslash-commands like \sum, \frac, etc.
    cleaned = re.sub(r"\\[a-zA-Z]+", "", cleaned)

    # 5. Build simple Sources section from retrieved chunks (group by file + pages)
    sources_by_file = defaultdict(lambda: {"pages": set(), "has_page": False})
    for c in candidates:
        entry = sources_by_file[c.file.file_name]
        if c.page_number:
            entry["pages"].add(c.page_number)
            entry["has_page"] = True

    sources_html = ""
    if sources_by_file:
        parts = ['<hr style="margin-top:16px;margin-bottom:8px;"/>']
        parts.append(
            '<div style="font-size:12px;color:#666;"><strong>Sources</strong>:<ul style="padding-left:18px;margin:4px 0;">'
        )
        for file_name, meta in sources_by_file.items():
            if meta["has_page"]:
                page_list = ", ".join(str(p) for p in sorted(meta["pages"]))
                label = f"{file_name} – page(s) {page_list}"
            else:
                label = file_name
            parts.append(f"<li>{label}</li>")
        parts.append("</ul></div>")
        sources_html = "".join(parts)

    final_html = cleaned + sources_html

    # 6. Persist AI message (and optionally metadata) when we are in a notebook.
    if notebook is not None:
        sources_meta = []
        for file_name, meta in sources_by_file.items():
            entry = {"file_name": file_name}
            if meta["has_page"]:
                entry["pages"] = sorted(meta["pages"])
            sources_meta.append(entry)

        ChatMessage.objects.create(
            notebook=notebook,
            role="ai",
            channel=channel,
            content_html=final_html,
            metadata={
                "question": question,
                "selected_text": selected_text,
                "sources": sources_meta,
            },
        )

    return Response({"html": final_html})


