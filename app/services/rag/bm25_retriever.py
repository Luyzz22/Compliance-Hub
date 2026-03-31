"""BM25 in-memory retriever for compliance document corpus.

Uses rank_bm25 (Okapi BM25) for term-frequency based retrieval.
Designed to be the primary retrieval path; dense retrieval is optional.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from app.services.rag.corpus import Document, RetrievalResult

logger = logging.getLogger(__name__)

_STOP_WORDS_DE = frozenset({
    "der", "die", "das", "ein", "eine", "und", "oder", "in", "von", "zu",
    "für", "mit", "auf", "ist", "sind", "wird", "werden", "bei", "den",
    "dem", "des", "als", "nach", "über", "unter", "an", "auch", "nicht",
    "sich", "es", "im", "wie", "dass", "nur", "noch", "aus", "wenn",
})


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"\w+", text.lower())
    return [t for t in tokens if t not in _STOP_WORDS_DE and len(t) > 1]


@dataclass
class BM25Index:
    documents: list[Document] = field(default_factory=list)
    _index: object | None = field(default=None, repr=False)

    def build(self, documents: list[Document]) -> None:
        self.documents = list(documents)
        if not self.documents:
            self._index = None
            return

        tokenized = [_tokenize(doc.content) for doc in self.documents]

        try:
            from rank_bm25 import BM25Okapi
            self._index = BM25Okapi(tokenized)
        except ImportError:
            logger.warning(
                "rank_bm25 not installed – using fallback TF scoring. "
                "Install with: pip install rank-bm25"
            )
            self._index = _FallbackTF(tokenized)

    def query(self, query_text: str, k: int = 5) -> list[RetrievalResult]:
        if not self._index or not self.documents:
            return []

        tokens = _tokenize(query_text)
        if not tokens:
            return []

        scores = self._index.get_scores(tokens)

        scored_docs = [
            (self.documents[i], float(scores[i]))
            for i in range(len(self.documents))
            if float(scores[i]) > 0
        ]
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        top_k = scored_docs[:k]

        max_score = top_k[0][1] if top_k else 1.0
        results = []
        for rank, (doc, raw_score) in enumerate(top_k):
            norm_score = raw_score / max_score if max_score > 0 else 0.0
            results.append(
                RetrievalResult(
                    doc=doc,
                    score=norm_score,
                    bm25_score=norm_score,
                    rank=rank + 1,
                    rescue_source="bm25",
                )
            )
        return results


class _FallbackTF:
    """Minimal term-frequency scorer when rank_bm25 is unavailable."""

    def __init__(self, tokenized_corpus: list[list[str]]) -> None:
        self._corpus = tokenized_corpus

    def get_scores(self, query_tokens: list[str]) -> list[float]:
        query_set = set(query_tokens)
        scores: list[float] = []
        for doc_tokens in self._corpus:
            overlap = sum(1 for t in doc_tokens if t in query_set)
            scores.append(overlap / max(len(doc_tokens), 1))
        return scores
