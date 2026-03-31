#!/usr/bin/env python3
"""
Ingest curated EU AI Act / NIS2 / ISO 42001 markdown into a Haystack InMemoryDocumentStore.

Pilot: loads ``app/rag/corpus/*.md`` by default, chunks paragraphs, prints document count.
For a custom directory::

  python scripts/ingest_eu_ai_act_nis2_corpus.py --corpus-dir /path/to/md

Optional dense index: ``--with-embeddings`` (downloads sentence-transformers model once).

See docs/architecture/wave6-hybrid-retrieval.md.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Repo root on PYTHONPATH when run as script from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from haystack.components.embedders import SentenceTransformersDocumentEmbedder
from haystack.document_stores.in_memory import InMemoryDocumentStore

from app.rag.haystack_config import rag_embedding_model_id
from app.rag.ingestion import load_corpus_from_directory, load_default_corpus_documents

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ingest_eu_ai_act_nis2_corpus")


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest regulatory RAG corpus (Haystack pilot).")
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=None,
        help="Directory containing .md files (default: app/rag/corpus)",
    )
    parser.add_argument(
        "--with-embeddings",
        action="store_true",
        help="Compute multilingual embeddings (same model as hybrid RAG runtime).",
    )
    args = parser.parse_args()
    if args.corpus_dir is not None:
        docs = load_corpus_from_directory(args.corpus_dir.resolve())
    else:
        docs = load_default_corpus_documents()
    if not docs:
        logger.error("no documents produced; check corpus paths")
        return 1
    store = InMemoryDocumentStore()
    store.write_documents(docs)
    if args.with_embeddings:
        mid = rag_embedding_model_id()
        logger.info("embedding_documents model_id=%s count=%s", mid, len(docs))
        embedder = SentenceTransformersDocumentEmbedder(model=mid)
        embedded = list(embedder.run(documents=docs)["documents"])
        store.delete_all_documents()
        store.write_documents(embedded)
    logger.info("ingested_documents count=%s store_type=in_memory", len(docs))
    for d in docs[:10]:
        logger.info("doc id=%s source=%s", d.id, (d.meta or {}).get("source"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
