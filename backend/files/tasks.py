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

    splitter = RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=20)
    split_docs = splitter.split_documents(docs)

    # Clean text chunks to avoid NUL bytes and empty strings, which Postgres does not accept.
    texts = []
    for d in split_docs:
        # Replace NUL characters with spaces and strip
        cleaned = (d.page_content or "").replace("\x00", " ").strip()
        if cleaned:
            texts.append(cleaned)

    if not texts:
        return

    embeddings_model = GoogleGenerativeAIEmbeddings(
        model="text-embedding-004",
        google_api_key=api_key,
    )

    vectors = embeddings_model.embed_documents(texts)

    DocumentEmbedding.objects.bulk_create(
        [
            DocumentEmbedding(file=pdf_file, text=text, embedding=vector)
            for text, vector in zip(texts, vectors)
        ]
    )


