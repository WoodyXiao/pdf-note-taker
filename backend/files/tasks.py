import os

from celery import shared_task
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from .models import DocumentEmbedding, PdfFile


@shared_task
def ingest_pdf_task(pdf_file_id: int) -> None:
    """
    Celery task to load a PDF from disk, split into chunks, embed, and store in the database.
    This mirrors the original Convex ingest pipeline but runs asynchronously via Celery.
    """
    api_key = os.getenv("NEXT_PUBLIC_GEMINI_API_KEY")
    if not api_key:
        # Fail fast so misconfiguration is obvious during development
        raise RuntimeError("NEXT_PUBLIC_GEMINI_API_KEY environment variable is not set")

    pdf_file = PdfFile.objects.get(id=pdf_file_id)

    loader = PyPDFLoader(pdf_file.file.path)
    docs = loader.load()

    # Use a slightly larger chunk size so we don't explode the chunk count on big books.
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    split_docs = splitter.split_documents(docs)

    # Clean text chunks to avoid NUL bytes and empty strings, which Postgres does not accept.
    texts: list[str] = []
    pages: list[int | None] = []
    for d in split_docs:
        # Replace NUL characters with spaces and strip
        cleaned = (d.page_content or "").replace("\x00", " ").strip()
        if cleaned:
            texts.append(cleaned)
            # PyPDFLoader provides 0-based "page" in metadata; store as 1-based.
            page_idx = d.metadata.get("page")
            if page_idx is not None:
                pages.append(int(page_idx) + 1)
            else:
                pages.append(None)

    if not texts:
        # Nothing meaningful extracted from this PDF; just return without creating embeddings.
        return

    embeddings_model = GoogleGenerativeAIEmbeddings(
        model="text-embedding-004",
        google_api_key=api_key,
    )

    # For very large documents, embed + insert in batches to avoid huge payloads/transactions.
    BATCH_SIZE = 256
    total = len(texts)

    for start in range(0, total, BATCH_SIZE):
        batch_texts = texts[start : start + BATCH_SIZE]
        batch_pages = pages[start : start + BATCH_SIZE]

        vectors = embeddings_model.embed_documents(batch_texts)

        DocumentEmbedding.objects.bulk_create(
            [
                DocumentEmbedding(
                    file=pdf_file,
                    text=text,
                    embedding=vector,
                    page_number=page,
                )
                for text, vector, page in zip(batch_texts, vectors, batch_pages)
            ]
        )


