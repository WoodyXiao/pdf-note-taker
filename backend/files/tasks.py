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
from langchain_google_genai import ChatGoogleGenerativeAI

from .models import DocumentChunk, DocumentEmbedding, PdfFile


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

        # Phase 1: try Unstructured by-title chunking; fallback to PyPDFLoader + splitter.
        chunks: list[dict] = []

        def _try_unstructured_chunks() -> list[dict]:
            try:
                from unstructured.partition.pdf import partition_pdf  # type: ignore
            except Exception:
                return []

            try:
                # Use Unstructured's native by-title chunking to keep chunk counts low (video-style).
                # We keep this text-only for Phase 1; table/image extraction comes later.
                max_characters = int(os.getenv("PDF_UNSTRUCTURED_MAX_CHARACTERS", "10000"))
                combine_under = int(
                    os.getenv("PDF_UNSTRUCTURED_COMBINE_UNDER_N_CHARS", "2000")
                )
                new_after = int(os.getenv("PDF_UNSTRUCTURED_NEW_AFTER_N_CHARS", "6000"))
                elements = partition_pdf(
                    filename=pdf_file.file.path,
                    chunking_strategy="by_title",
                    max_characters=max_characters,
                    combine_text_under_n_chars=combine_under,
                    new_after_n_chars=new_after,
                )
            except Exception:
                return []

            def _clean_text(v: str) -> str:
                return (v or "").replace("\x00", " ").strip()

            def _extract_title_and_pages_from_orig(chunk) -> tuple[str, int | None, int | None]:
                title = ""
                pages: list[int] = []
                orig = getattr(getattr(chunk, "metadata", None), "orig_elements", None)
                if orig:
                    for el in orig:
                        # title
                        if not title and ("Title" in str(type(el))):
                            title = _clean_text(getattr(el, "text", ""))
                        # pages
                        pn = getattr(getattr(el, "metadata", None), "page_number", None)
                        if pn is not None:
                            try:
                                pages.append(int(pn))
                            except Exception:
                                pass
                page_start = min(pages) if pages else None
                page_end = max(pages) if pages else None
                return title, page_start, page_end

            out: list[dict] = []
            for chunk in elements:
                # Phase 1: only accept text composite elements.
                if "CompositeElement" not in str(type(chunk)):
                    continue
                raw = _clean_text(getattr(chunk, "text", ""))
                if not raw:
                    continue
                title, page_start, page_end = _extract_title_and_pages_from_orig(chunk)
                out.append(
                    {
                        "title": title,
                        "raw_text": raw,
                        "page_start": page_start,
                        "page_end": page_end,
                    }
                )

            return out

        chunks = _try_unstructured_chunks()

        if not chunks:
            # Fallback: use PyPDFLoader per-page docs and split.
            splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
            split_docs = splitter.split_documents(docs)
            texts: list[str] = []
            pages: list[int | None] = []
            for d in split_docs:
                cleaned = (d.page_content or "").replace("\x00", " ").strip()
                if cleaned:
                    texts.append(cleaned)
                    page_idx = d.metadata.get("page")
                    pages.append(int(page_idx) + 1 if page_idx is not None else None)

            # Each split chunk becomes a DocumentChunk
            for text, page in zip(texts, pages):
                chunks.append(
                    {
                        "title": "",
                        "raw_text": text,
                        "page_start": page,
                        "page_end": page,
                    }
                )

        if chunks:
            # Update total chunks now that we know it.
            try:
                pdf_file.ingest_total_chunks = len(chunks)
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

            # Summarize each chunk for retrieval (embed summaries, not raw text).
            # api_key already validated above
            api_key = os.getenv("NEXT_PUBLIC_GEMINI_API_KEY")
            model_id = os.getenv("GEMINI_CHAT_MODEL", "gemini-flash-latest")
            summary_mode = os.getenv("PDF_SUMMARY_MODE", "llm").lower()
            max_llm_chunks = int(os.getenv("PDF_SUMMARY_MAX_LLM_CHUNKS_PER_PDF", "24"))
            summary_batch_size = int(os.getenv("PDF_SUMMARY_BATCH_SIZE", "3"))
            truncate_chars = int(os.getenv("PDF_SUMMARY_TRUNCATE_CHARS", "1800"))

            summarizer = None
            if summary_mode == "llm":
                summarizer = ChatGoogleGenerativeAI(
                    model=model_id,
                    temperature=0.2,
                    max_output_tokens=1024,
                    google_api_key=api_key,
                )

            def _is_quota_exc(exc: Exception) -> bool:
                msg = str(exc)
                return ("RESOURCE_EXHAUSTED" in msg) or ("429" in msg)

            def _truncate_summary(title: str, raw_text: str) -> str:
                head = raw_text[:truncate_chars].strip()
                if title:
                    return f"{title}\n{head}"
                return head

            def _summarize_batch_llm(batch: list[dict]) -> list[str]:
                """
                Summarize multiple chunks in one LLM call to reduce request count.
                Returns list of summaries aligned to batch order.
                Falls back to truncation on any failure (especially quota).
                """
                if not summarizer:
                    return [_truncate_summary(c.get("title", ""), c.get("raw_text", "")) for c in batch]

                # Build a compact, JSON-only prompt so parsing is reliable.
                items = []
                for i, c in enumerate(batch, start=1):
                    title = (c.get("title") or "").strip()
                    raw = (c.get("raw_text") or "").strip()
                    items.append(
                        {
                            "index": i,
                            "title": title,
                            "text": raw,
                        }
                    )

                prompt = (
                    "You will be given a JSON array of document chunks.\n"
                    "For each item, write a concise retrieval summary emphasizing key terms, definitions, entities, and numbers.\n"
                    "Return ONLY valid JSON: an array of strings, same length and order as input.\n\n"
                    f"Input:\n{json.dumps(items, ensure_ascii=False)}\n"
                )

                try:
                    res = summarizer.invoke(prompt)
                    content = getattr(res, "content", res)
                    if isinstance(content, list):
                        # Join any text parts into one string
                        parts = []
                        for part in content:
                            if isinstance(part, dict) and part.get("type") == "text":
                                parts.append(part.get("text", ""))
                            else:
                                parts.append(str(part))
                        content = "\n".join(parts)
                    raw = str(content).strip()

                    # Try parse JSON array
                    parsed = json.loads(raw)
                    if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed) and len(parsed) == len(batch):
                        return [x.strip() for x in parsed]
                except Exception as exc:
                    if _is_quota_exc(exc):
                        # Quota hit: don't block ingestion; fall back immediately.
                        return [_truncate_summary(c.get("title", ""), c.get("raw_text", "")) for c in batch]
                    # Non-quota failure: fall back for safety
                    return [_truncate_summary(c.get("title", ""), c.get("raw_text", "")) for c in batch]

                # Parse failed or malformed output: fall back
                return [_truncate_summary(c.get("title", ""), c.get("raw_text", "")) for c in batch]

            embeddings_model = GoogleGenerativeAIEmbeddings(
                model="text-embedding-004",
                google_api_key=api_key,
            )

            # For very large documents, embed + insert in batches to avoid huge payloads/transactions.
            BATCH_SIZE = 256
            total = len(chunks)
            last_publish_ts = 0.0
            last_publish_progress = -5

            for start in range(0, total, BATCH_SIZE):
                # If the file was deleted while ingesting, stop immediately.
                if not PdfFile.objects.filter(id=pdf_file_id).exists():
                    return

                batch_chunks = chunks[start : start + BATCH_SIZE]

                # Limit the number of LLM summary calls per PDF to avoid quota exhaustion.
                # After we reach the cap, we use a cheap truncation-based summary for retrieval indexing.
                batch_summaries: list[str] = []
                if summary_mode == "llm":
                    llm_budget_remaining = max(0, max_llm_chunks - start)
                else:
                    llm_budget_remaining = 0

                if summarizer and llm_budget_remaining > 0:
                    # Summarize up to the remaining budget, in batches (reduces API call count).
                    to_llm = batch_chunks[:llm_budget_remaining]
                    to_trunc = batch_chunks[llm_budget_remaining:]

                    for s in range(0, len(to_llm), max(1, summary_batch_size)):
                        sub = to_llm[s : s + max(1, summary_batch_size)]
                        batch_summaries.extend(_summarize_batch_llm(sub))

                    # Fill the rest with truncation
                    for c in to_trunc:
                        batch_summaries.append(_truncate_summary(c.get("title", ""), c.get("raw_text", "")))
                else:
                    # No LLM summaries (either mode=truncate or budget exhausted)
                    for c in batch_chunks:
                        batch_summaries.append(_truncate_summary(c.get("title", ""), c.get("raw_text", "")))

                vectors = embeddings_model.embed_documents(batch_summaries)

                # Re-check right before writing, in case deletion happened during the API call.
                if not PdfFile.objects.filter(id=pdf_file_id).exists():
                    return

                try:
                    # Create doc store rows for this batch.
                    chunk_rows = []
                    for c in batch_chunks:
                        chunk_rows.append(
                            DocumentChunk(
                                file=pdf_file,
                                chunk_type=DocumentChunk.TYPE_TEXT,
                                title=c.get("title", "") or "",
                                page_start=c.get("page_start"),
                                page_end=c.get("page_end"),
                                raw_text=c.get("raw_text", "") or "",
                            )
                        )
                    DocumentChunk.objects.bulk_create(chunk_rows)

                    DocumentEmbedding.objects.bulk_create(
                        [
                            DocumentEmbedding(
                                file=pdf_file,
                                chunk=chunk_row,
                                text=summary,
                                embedding=vector,
                                page_number=chunk_row.page_start,
                            )
                            for chunk_row, summary, vector in zip(
                                chunk_rows, batch_summaries, vectors
                            )
                        ]
                    )
                except IntegrityError:
                    # Most likely: PdfFile was deleted and FK insert fails.
                    return

                # Progress update (throttled): every 5% or at least every 2 seconds.
                try:
                    done = (pdf_file.ingest_done_chunks or 0) + len(batch_chunks)
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


