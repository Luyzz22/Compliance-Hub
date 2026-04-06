"""Document corpus model for the RAG pipeline.

Documents are compliance regulation sections (EU AI Act, ISO 42001, NIS2, etc.).
No PII is stored—only regulatory text, metadata, and tenant-specific guidance flags.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Document:
    doc_id: str
    title: str
    content: str
    source: str
    section: str = ""
    metadata: dict[str, str] = field(default_factory=dict)
    is_tenant_guidance: bool = False
    """True if this document is tenant-specific guidance (not global law text)."""


@dataclass
class RetrievalResult:
    doc: Document
    score: float
    bm25_score: float = 0.0
    dense_score: float = 0.0
    rank: int = 0
    rescue_source: str = "bm25"
    """Which retriever was primarily responsible: 'bm25', 'dense', or 'both'."""


@dataclass
class RetrievalResponse:
    results: list[RetrievalResult]
    retrieval_mode: str
    alpha_used: float
    query_hash: str
    confidence_level: str = "low"
    confidence_score: float = 0.0
    has_tenant_guidance: bool = False
