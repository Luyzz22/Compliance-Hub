"""Optional dense (embedding-based) retriever for hybrid RAG.

Gracefully degrades to a no-op if sentence-transformers is not installed.
Uses cosine similarity on multilingual embeddings.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np

from app.services.rag.corpus import Document, RetrievalResult

logger = logging.getLogger(__name__)


@dataclass
class DenseIndex:
    documents: list[Document] = field(default_factory=list)
    _embeddings: np.ndarray | None = field(default=None, repr=False)
    _model: object | None = field(default=None, repr=False)
    _available: bool = field(default=False, repr=False)
    model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    def build(self, documents: list[Document], model_name: str | None = None) -> None:
        self.documents = list(documents)
        if model_name:
            self.model_name = model_name

        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
            texts = [doc.content for doc in self.documents]
            self._embeddings = self._model.encode(texts, normalize_embeddings=True)
            self._available = True
            logger.info(
                "Dense index built with %d documents using %s",
                len(documents),
                self.model_name,
            )
        except ImportError:
            logger.info(
                "sentence-transformers not installed – dense retrieval disabled. "
                "Install with: pip install sentence-transformers"
            )
            self._available = False
        except Exception as exc:
            # Network/proxy/model-download errors must not break request or tests:
            # hybrid mode should degrade to BM25-only retrieval.
            logger.warning(
                "Dense retrieval disabled due to model load error for %s: %s",
                self.model_name,
                exc,
            )
            self._model = None
            self._embeddings = None
            self._available = False

    @property
    def is_available(self) -> bool:
        return self._available

    def query(self, query_text: str, k: int = 5) -> list[RetrievalResult]:
        if not self._available or self._embeddings is None or not self.documents:
            return []

        query_emb = self._model.encode([query_text], normalize_embeddings=True)
        similarities = np.dot(self._embeddings, query_emb.T).flatten()

        top_indices = np.argsort(similarities)[::-1][:k]
        results = []
        for rank, idx in enumerate(top_indices):
            sim = float(similarities[idx])
            if sim <= 0:
                continue
            results.append(
                RetrievalResult(
                    doc=self.documents[idx],
                    score=sim,
                    dense_score=sim,
                    rank=rank + 1,
                    rescue_source="dense",
                )
            )
        return results
