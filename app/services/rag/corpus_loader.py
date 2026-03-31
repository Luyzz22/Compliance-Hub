from __future__ import annotations

import json
import os
from pathlib import Path

from app.services.rag.corpus import Document

_FALLBACK: list[Document] = [
    Document(
        doc_id="eu-ai-act-high-risk",
        title="Hochrisiko",
        content="Anlage III EU AI Act nennt Hochrisiko-KI-Systeme in acht Bereichen.",
        source="EU AI Act",
        section="Anlage III",
    ),
    Document(
        doc_id="nis2-incident-deadline",
        title="Meldung",
        content="NIS2: erhebliche Vorfälle sind ohne schuldhaftes Verzögern zu melden.",
        source="NIS2",
        section="Art. 23",
    ),
]


def default_corpus_path() -> Path:
    env = os.environ.get("ADVISOR_RAG_CORPUS_PATH", "").strip()
    if env:
        return Path(env)
    return Path(__file__).resolve().parent / "default_corpus.json"


def load_advisor_corpus(path: Path | None = None) -> list[Document]:
    p = path or default_corpus_path()
    if not p.is_file():
        return list(_FALLBACK)
    raw = json.loads(p.read_text(encoding="utf-8"))
    items = raw.get("corpus") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        return list(_FALLBACK)
    out: list[Document] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        doc_id = item.get("doc_id")
        content = item.get("content") or item.get("text")
        if not doc_id or not content:
            continue
        meta = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        tg = bool(meta.get("tenant_guidance")) or bool(item.get("is_tenant_guidance"))
        out.append(
            Document(
                doc_id=str(doc_id),
                title=str(item.get("title") or doc_id),
                content=str(content),
                source=str(item.get("source") or ""),
                section=str(item.get("section") or ""),
                metadata={str(k): str(v) for k, v in meta.items()},
                is_tenant_guidance=tg,
            )
        )
    return out if out else list(_FALLBACK)
