# Wave 6: Hybrid retrieval (BM25 + dense embeddings) — advisor EU regulatory RAG

## Why hybrid

Lexical **BM25** is fast and auditable but can **miss paraphrases** (especially German legal wording that does not repeat query keywords). **Dense embeddings** improve **recall** on semantically equivalent questions while remaining explainable if we log **per-path scores** and **document IDs only** (no raw prompts in evidence).

Hybrid mode is **opt-in** via environment (default remains BM25 until validated in production).

## Configuration

| Variable | Meaning |
|----------|---------|
| `COMPLIANCEHUB_ADVISOR_RAG_RETRIEVAL_MODE` | `bm25` (default) or `hybrid` |
| `COMPLIANCEHUB_RAG_RETRIEVER` | Legacy: value `embedding` maps to `hybrid` |
| `COMPLIANCEHUB_RAG_EMBEDDING_MODEL` | Hugging Face id for document + query embedder |
| `COMPLIANCEHUB_RAG_HYBRID_DENSE_ALPHA` | Convex mix: `(1-α)*norm_bm25 + α*norm_dense`, default `0.5` |
| `COMPLIANCEHUB_RAG_HYBRID_POOL_K` | Candidate pool before re-ranking to merged top-k (default `24`, max `50`) |
| `COMPLIANCEHUB_RAG_HYBRID_MIN_COMBINED_SCORE` | Minimum **combined** score for LLM context (default `0.22`) |
| `COMPLIANCEHUB_RAG_HYBRID_RESCUE_EMBEDDING_MIN` | If BM25 is below `COMPLIANCEHUB_RAG_BM25_MIN_SCORE`, a hit can still pass if **raw cosine** dense score ≥ this floor (default `0.62`; Haystack `scale_score=True` is avoided so scores stay spread in `[0,1]` for typical directions) |
| `COMPLIANCEHUB_RAG_HYBRID_CONFIDENCE_HIGH_MIN` / `_GAP_MIN` | High-confidence heuristic on **combined** scores |

## Score combination (auditor-readable)

1. Retrieve **BM25** and **dense** candidates separately (same global / tenant metadata filters as Wave 3).
2. Within each channel, normalize scores to **[0, 1]** by dividing by the max score in that channel’s candidate pool (separate normalization per channel).
3. **Combined** (convex): `(1 - α) * bm25_norm + α * dense_norm`.
4. Sort by `combined`, keep merged top-k (`COMPLIANCEHUB_RAG_MERGED_TOP_K`).

## Confidence heuristics (Option B)

- **BM25 min score** remains a **lexical guardrail** (`COMPLIANCEHUB_RAG_BM25_MIN_SCORE`).
- **Hybrid gate**: a document enters the LLM prompt if **any** of:
  - `combined >= hybrid_min_combined`, or
  - `bm25 >= bm25_min`, or
  - `embedding_score >= rescue_embedding_min` (raw cosine similarity from `InMemoryEmbeddingRetriever` with `scale_score=False`).

Confidence **high / medium / low** uses the **combined** scores on the filtered set, with hybrid-specific `high` and `gap` thresholds so labels stay meaningful on the [0,1]-ish combined scale.

## Execution graph (unchanged shape)

Still explicit in `app/rag/pipelines/eu_ai_act_nis2_pipeline.py`:

`Query → (BM25 | hybrid retrieval) → quality gate → confidence → PromptBuilder → Generator`

Hybrid adds **no hidden nodes**: BM25 uses `InMemoryBM25Retriever`; dense uses `InMemoryEmbeddingRetriever` with **precomputed** document embeddings in the same `InMemoryDocumentStore`.

## Embeddings lifecycle

- **Runtime:** `ensure_document_store_embeddings` embeds any document missing `embedding` (lazy, once per process/store) using `SentenceTransformersDocumentEmbedder`.
- **Offline:** `scripts/ingest_eu_ai_act_nis2_corpus.py --with-embeddings` writes an embedded corpus for inspection (still in-memory in the script; production persistence is future work).

## Observability and evidence

- `log_rag_query_event` `extra` includes `retrieval_mode`, and for hybrid `hybrid_alpha` and `retrieval_hit_audit` (per doc: `doc_id`, `bm25_score`, `embedding_score`, `combined_score`, `rag_scope`, `is_tenant_guidance`).
- Advisor API `EuAiActNis2RagResponse` optionally returns `retrieval_mode` and `retrieval_hit_audit` for the same audit payload shape.
- Audit events (`advisor_regulatory_rag`) persist `retrieval_mode` and `retrieval_hit_audit` in metadata.
- AI Act Evidence detail (`AiEvidenceRagDetailSection`) exposes `retrieval_mode` and `score_audit` for the Compliance UI.

Raw **questions** are never stored in evidence; only **hashes**, **IDs**, and **scores**.

## See also

- [wave3-haystack-rag.md](./wave3-haystack-rag.md) — baseline BM25 pilot
- [wave4-observability.md](./wave4-observability.md) — tracing + `log_rag_query_event`
