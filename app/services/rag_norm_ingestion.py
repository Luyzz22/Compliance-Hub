"""RAG norm ingestion — chunks regulatory texts and stores embeddings (Phase 3).

Supports EU AI Act, ISO 42001, NIS2, DSGVO article-level chunking.
Embedding model configurable via COMPLIANCEHUB_NORM_EMBEDDING_MODEL env var.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models_db import NormEmbeddingDB

logger = logging.getLogger(__name__)

NORM_EMBEDDING_MODEL = os.getenv("COMPLIANCEHUB_NORM_EMBEDDING_MODEL", "text-embedding-3-large")


def chunk_article_text(
    norm: str,
    article_ref: str,
    text: str,
    *,
    max_chunk_size: int = 1500,
) -> list[dict]:
    """Split article text into overlapping chunks with metadata."""
    chunks = []
    paragraphs = text.split("\n\n")
    current_chunk = ""
    chunk_idx = 0

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 > max_chunk_size and current_chunk:
            chunks.append(
                {
                    "norm": norm,
                    "article_ref": article_ref,
                    "chunk_index": chunk_idx,
                    "text_content": current_chunk.strip(),
                }
            )
            chunk_idx += 1
            current_chunk = para
        else:
            current_chunk = current_chunk + "\n\n" + para if current_chunk else para

    if current_chunk.strip():
        chunks.append(
            {
                "norm": norm,
                "article_ref": article_ref,
                "chunk_index": chunk_idx,
                "text_content": current_chunk.strip(),
            }
        )
    return chunks


def ingest_norm_chunks(
    session: Session,
    *,
    norm: str,
    article_ref: str,
    text_content: str,
    valid_from: str | None = None,
    metadata: dict | None = None,
    embedding_model: str | None = None,
) -> list[NormEmbeddingDB]:
    """Chunk and store norm text into norm_embeddings table."""
    model = embedding_model or NORM_EMBEDDING_MODEL
    chunks = chunk_article_text(norm, article_ref, text_content)
    rows = []
    for chunk in chunks:
        row = NormEmbeddingDB(
            id=str(uuid.uuid4()),
            norm=chunk["norm"],
            article_ref=chunk["article_ref"],
            chunk_index=chunk["chunk_index"],
            text_content=chunk["text_content"],
            embedding_json=None,  # computed async or via batch
            embedding_model=model,
            valid_from=valid_from,
            metadata_json=json.dumps(metadata) if metadata else None,
            created_at_utc=datetime.now(UTC),
        )
        session.add(row)
        rows.append(row)
    session.flush()
    return rows


def search_norm_chunks(
    session: Session,
    *,
    norm: str | None = None,
    query_text: str = "",
    limit: int = 10,
) -> list[dict]:
    """Simple text-based search over norm embeddings (BM25-style fallback).

    In production with pgvector, this would be a cosine similarity search.
    """
    stmt = select(NormEmbeddingDB)
    if norm:
        stmt = stmt.where(NormEmbeddingDB.norm == norm)
    if query_text:
        stmt = stmt.where(NormEmbeddingDB.text_content.contains(query_text))
    stmt = stmt.limit(limit)

    rows = session.execute(stmt).scalars().all()
    return [
        {
            "id": r.id,
            "norm": r.norm,
            "article_ref": r.article_ref,
            "chunk_index": r.chunk_index,
            "text_content": r.text_content,
            "embedding_model": r.embedding_model,
            "valid_from": r.valid_from,
        }
        for r in rows
    ]
