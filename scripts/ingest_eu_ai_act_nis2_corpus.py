#!/usr/bin/env python3
"""
Ingest curated EU AI Act / NIS2 / ISO 42001 markdown into a Haystack InMemoryDocumentStore.

Pilot: loads ``app/rag/corpus/*.md`` by default, chunks paragraphs, prints document count.
For a custom directory::

  python scripts/ingest_eu_ai_act_nis2_corpus.py --corpus-dir /path/to/md

Future: extend with pgvector / FAISS persistence (see docs/architecture/wave3-haystack-rag.md).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Repo root on PYTHONPATH when run as script from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from haystack.document_stores.in_memory import InMemoryDocumentStore

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
    logger.info("ingested_documents count=%s store_type=in_memory", len(docs))
    for d in docs[:10]:
        logger.info("doc id=%s source=%s", d.id, (d.meta or {}).get("source"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
