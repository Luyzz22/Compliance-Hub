"""Load and chunk curated markdown into Haystack Documents (ingestion + runtime seed)."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from haystack import Document

logger = logging.getLogger(__name__)

_DEFAULT_CORPUS_DIR = Path(__file__).resolve().parent / "corpus"


def _slug_from_filename(path: Path) -> str:
    stem = path.stem.lower()
    return re.sub(r"[^a-z0-9]+", "-", stem).strip("-") or "doc"


def documents_from_markdown_files(
    paths: list[Path],
    *,
    max_chunks_per_file: int = 24,
) -> list[Document]:
    """
    Split each markdown file into paragraph-ish chunks with stable metadata.

    ``doc_id`` format: ``{file_slug}-chunk-{n}`` for audit traceability.
    """
    out: list[Document] = []
    for path in paths:
        if not path.is_file():
            logger.warning("rag_ingest_skip_missing path=%s", path)
            continue
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        title_line = next(
            (ln.strip("# ").strip() for ln in text.splitlines() if ln.strip()),
            path.stem,
        )
        source_hint = path.name
        slug = _slug_from_filename(path)
        parts = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
        chunks = parts[:max_chunks_per_file]
        for i, chunk in enumerate(chunks):
            doc_id = f"{slug}-chunk-{i}"
            meta = {
                "source": source_hint,
                "section": title_line[:200],
                "article": slug,
                "rag_scope": "global",
            }
            out.append(Document(id=doc_id, content=chunk, meta=meta))
    return out


def load_default_corpus_documents() -> list[Document]:
    """Shipped pilot corpus under ``app/rag/corpus``."""
    if not _DEFAULT_CORPUS_DIR.is_dir():
        return []
    md_files = sorted(_DEFAULT_CORPUS_DIR.glob("*.md"))
    return documents_from_markdown_files(md_files)


def load_corpus_from_directory(corpus_dir: Path) -> list[Document]:
    if not corpus_dir.is_dir():
        raise FileNotFoundError(f"corpus directory not found: {corpus_dir}")
    md_files = sorted(corpus_dir.glob("*.md"))
    if not md_files:
        raise ValueError(f"no .md files under {corpus_dir}")
    return documents_from_markdown_files(md_files)
