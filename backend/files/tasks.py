import json
import os
import time

import redis
from celery import shared_task
from django.db import IntegrityError
from django.utils import timezone
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from .models import DocumentEmbedding, PdfFile


def _publish_ingest_event(pdf_file: PdfFile) -> None:
  """
  Publish a lightweight ingest status event to Redis for SSE consumers.

  Failures here should never break the main ingest task, so we swallow errors.
  """
  try:
      redis_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
      r = redis.from_url(redis_url)
      payload = {
          "type": "pdf_ingested",
          "file_id": str(pdf_file.file_id),
          "is_ingested": pdf_file.is_ingested,
          "ingest_error": pdf_file.ingest_error,
          "ingest_status": getattr(pdf_file, "ingest_status", None),
          "ingest_progress": getattr(pdf_file, "ingest_progress", None),
          "ingest_done_chunks": getattr(pdf_file, "ingest_done_chunks", None),
          "ingest_total_chunks": getattr(pdf_file, "ingest_total_chunks", None),
          "ingest_started_at": pdf_file.ingest_started_at.isoformat()
          if getattr(pdf_file, "ingest_started_at", None)
          else None,
          "ingest_finished_at": pdf_file.ingest_finished_at.isoformat()
          if getattr(pdf_file, "ingest_finished_at", None)
          else None,
      }
      r.publish("pdf_ingest_events", json.dumps(payload))
  except Exception:
      # Best-effort only; log in Celery output but don't crash the task.
      return


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

    try:
        pdf_file = PdfFile.objects.get(id=pdf_file_id)
    except PdfFile.DoesNotExist:
        # The file was deleted before we started; nothing to do.
        return

    # Reset ingest flags before starting.
    pdf_file.is_ingested = False
    pdf_file.ingest_error = None
    pdf_file.ingest_status = PdfFile.INGEST_RUNNING
    pdf_file.ingest_progress = 0
    pdf_file.ingest_done_chunks = 0
    pdf_file.ingest_total_chunks = None
    pdf_file.ingest_started_at = timezone.now()
    pdf_file.ingest_finished_at = None
    pdf_file.save(update_fields=["is_ingested", "ingest_error"])
    # Save new fields if they exist (older DBs might not have migrated yet).
    try:
        pdf_file.save(
            update_fields=[
                "ingest_status",
                "ingest_progress",
                "ingest_done_chunks",
                "ingest_total_chunks",
                "ingest_started_at",
                "ingest_finished_at",
            ]
        )
    except Exception:
        pass
    _publish_ingest_event(pdf_file)

    try:
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

        if texts:
            # Update total chunks now that we know it.
            try:
                pdf_file.ingest_total_chunks = len(texts)
                pdf_file.ingest_done_chunks = 0
                pdf_file.ingest_progress = 0
                pdf_file.save(
                    update_fields=[
                        "ingest_total_chunks",
                        "ingest_done_chunks",
                        "ingest_progress",
                    ]
                )
                _publish_ingest_event(pdf_file)
            except Exception:
                pass

            embeddings_model = GoogleGenerativeAIEmbeddings(
                model="text-embedding-004",
                google_api_key=api_key,
            )

            # For very large documents, embed + insert in batches to avoid huge payloads/transactions.
            BATCH_SIZE = 256
            total = len(texts)
            last_publish_ts = 0.0
            last_publish_progress = -5

            for start in range(0, total, BATCH_SIZE):
                # If the file was deleted while ingesting, stop immediately.
                if not PdfFile.objects.filter(id=pdf_file_id).exists():
                    return

                batch_texts = texts[start : start + BATCH_SIZE]
                batch_pages = pages[start : start + BATCH_SIZE]

                vectors = embeddings_model.embed_documents(batch_texts)

                # Re-check right before writing, in case deletion happened during the API call.
                if not PdfFile.objects.filter(id=pdf_file_id).exists():
                    return

                try:
                    DocumentEmbedding.objects.bulk_create(
                        [
                            DocumentEmbedding(
                                file=pdf_file,
                                text=text,
                                embedding=vector,
                                page_number=page,
                            )
                            for text, vector, page in zip(
                                batch_texts, vectors, batch_pages
                            )
                        ]
                    )
                except IntegrityError:
                    # Most likely: PdfFile was deleted and FK insert fails.
                    return

                # Progress update (throttled): every 5% or at least every 2 seconds.
                try:
                    done = (pdf_file.ingest_done_chunks or 0) + len(batch_texts)
                    total_chunks = pdf_file.ingest_total_chunks or total
                    progress = int((done / max(total_chunks, 1)) * 100)
                    progress = max(0, min(100, progress))

                    # Keep local counters for this task run
                    pdf_file.ingest_done_chunks = done
                    pdf_file.ingest_progress = progress

                    now_ts = time.time()
                    last_ts = last_publish_ts
                    last_progress = last_publish_progress

                    should_publish = (
                        progress >= last_progress + 5 or (now_ts - last_ts) >= 2.0
                    )
                    if should_publish:
                        last_publish_ts = now_ts
                        last_publish_progress = progress
                        pdf_file.save(
                            update_fields=["ingest_done_chunks", "ingest_progress"]
                        )
                        _publish_ingest_event(pdf_file)
                except Exception:
                    pass

        # Mark ingest as finished (even if no texts; there is nothing more to do).
        if not PdfFile.objects.filter(id=pdf_file_id).exists():
            return
        pdf_file.is_ingested = True
        pdf_file.ingest_error = None
        pdf_file.ingest_status = PdfFile.INGEST_SUCCEEDED
        pdf_file.ingest_progress = 100
        pdf_file.ingest_finished_at = timezone.now()
        pdf_file.save(update_fields=["is_ingested", "ingest_error"])
        try:
            pdf_file.save(
                update_fields=[
                    "ingest_status",
                    "ingest_progress",
                    "ingest_finished_at",
                    "ingest_done_chunks",
                    "ingest_total_chunks",
                ]
            )
        except Exception:
            pass
        _publish_ingest_event(pdf_file)

    except Exception as exc:  # pragma: no cover - defensive logging
        if not PdfFile.objects.filter(id=pdf_file_id).exists():
            return
        # Record the error so the UI can stop showing an infinite spinner.
        pdf_file.is_ingested = True
        pdf_file.ingest_error = str(exc)
        pdf_file.ingest_status = PdfFile.INGEST_FAILED
        pdf_file.ingest_progress = 100
        pdf_file.ingest_finished_at = timezone.now()
        pdf_file.save(update_fields=["is_ingested", "ingest_error"])
        try:
            pdf_file.save(
                update_fields=[
                    "ingest_status",
                    "ingest_progress",
                    "ingest_finished_at",
                    "ingest_done_chunks",
                    "ingest_total_chunks",
                ]
            )
        except Exception:
            pass
        _publish_ingest_event(pdf_file)
        # Let Celery still record the exception for logs/monitoring.
        raise


