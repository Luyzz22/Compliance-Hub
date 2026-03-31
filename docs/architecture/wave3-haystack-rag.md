# Wave 3: Haystack RAG — EU AI Act / NIS2 / ISO 42001 Knowledge Hub (pilot)

## Why Haystack

ComplianceHub needs **retrieval-augmented** answers that are **explainable in audits**: which sources were seen, which model generated the answer, and which policy gates ran. Haystack 2 fits because:

- **Explicit pipeline graphs** (components + `Pipeline.connect`) keep retrieval and prompt construction visible in code, not buried in ad-hoc strings.
- **Swappable document stores** (in-memory for tests, later Postgres + pgvector or managed vector DB) without rewriting business logic.
- Strong adoption in **European** NLP / enterprise search contexts and good fit next to our existing Python stack.

## Pilot scope

- **Use case:** Advisors ask **German** questions about **EU AI Act**, **NIS2**, and **ISO 42001** using a **small curated corpus** under `app/rag/corpus/` (markdown snippets, not full legal texts).
- **Retriever (v1):** **BM25** (`InMemoryBM25Retriever`) over `InMemoryDocumentStore` — fast, deterministic in CI.
- **Generator:** `generate_eu_reg_rag_llm_output` → **`safe_llm_call_sync`** with `EuRegRagLlmOutput` (JSON) and **`LlmCallContext`** (`action_name=advisor_rag_eu_ai_act_nis2_query`).
- **API:** `POST /api/v1/advisor/rag/eu-ai-act-nis2-query` with OPA **`advisor_rag_eu_ai_act_nis2_query`**, headers `x-api-key` + **`x-advisor-id`**, feature flag **`COMPLIANCEHUB_FEATURE_COMPLIANCE_RAG_KNOWLEDGE_HUB`**.

Configuration: `app/rag/haystack_config.py`.

## Execution graph (explicit, auditable)

Implemented as a **fixed sequence** in `app/rag/pipelines/eu_ai_act_nis2_pipeline.py` (no hidden lambdas):

1. **`merged_bm25_retrieve`** (`app/rag/retrieval.py`) — always queries **global** snippets (`meta.rag_scope == global`); optionally **tenant guidance** (`rag_scope == tenant_guidance` + `meta.tenant_id`).
2. **`filter_documents_by_min_score`** — drops weak BM25 hits (`COMPLIANCEHUB_RAG_BM25_MIN_SCORE`, default `0.08`).
3. **`compute_confidence_level`** (`app/rag/confidence.py`) — coarse **high / medium / low** from best score and top-1 vs top-2 gap (`COMPLIANCEHUB_RAG_CONFIDENCE_*`).
4. If nothing passes the threshold: **no LLM call**; returns a **safe German** stock answer and `confidence_level=low` plus `notes_de`.
5. **`build_eu_reg_rag_prompt`** (`app/rag/prompting.py`) — catalog labels **EU/NIS2/ISO-Korpus** vs **Mandanten-Leitfaden**.
6. **`generate_eu_reg_rag_llm_output`** (`app/rag/generation.py`) — guardrailed structured answer.

Top-k caps (each max 10): `COMPLIANCEHUB_RAG_GLOBAL_TOP_K`, `COMPLIANCEHUB_RAG_TENANT_TOP_K`, merged cap `COMPLIANCEHUB_RAG_MERGED_TOP_K` (alias: legacy `COMPLIANCEHUB_RAG_TOP_K`).

## Observability

`log_rag_query_event` in `app/rag/observability.py` emits **two** JSON log lines per request:

- **`retrieval_complete`:** `query_sha256`, length, **redacted** preview (long digit runs masked), `retrieved_doc_ids`, `retrieval_scores`, `top_k_effective`, retrieval latency.
- **`response_complete`:** same hash/preview identifiers, optional LLM latency, total latency, `confidence_level`, `extra.used_llm` / hit counts.

Raw `question_de` is **not** logged.

## Tenant-scoping

- **Global law / norm pilot text:** `meta.rag_scope = "global"` (set automatically in `documents_from_markdown_files`).
- **Tenant overlays:** documents with `meta.rag_scope = "tenant_guidance"` and `meta.tenant_id = "<tenant>"`. Helper: `register_tenant_guidance_documents` in `app/rag/store.py`.
- API citations include **`is_tenant_specific`** (true for tenant guidance). Legacy fields **`doc_id`**, **`source`**, **`section`** remain; added **`source_id`** (defaults to `doc_id`) and **`title`**.

## API response (advisory)

`EuAiActNis2RagResponse` includes:

- `answer_de`, `citations`, **`confidence_level`**, optional **`notes_de`**.

**Advisory notice:** RAG output is **not legal advice**. For **`low`** or **`medium`** confidence, `notes_de` prompts human review. Operators should treat the feature as **decision support** only.

## Ingestion

`scripts/ingest_eu_ai_act_nis2_corpus.py` loads `.md` files; chunks get `rag_scope=global` unless extended for tenant uploads.

## Hybrid retrieval (Wave 6)

Optional **BM25 + dense** mode is documented in [wave6-hybrid-retrieval.md](./wave6-hybrid-retrieval.md) (`COMPLIANCEHUB_ADVISOR_RAG_RETRIEVAL_MODE=hybrid`).

## Integration outlook

- **Temporal (Wave 2):** RAG can run inside an activity with the same guardrails and logging hooks.
- **Advisor / board flows:** attach `query_sha256`, doc ids, and `confidence_level` to workflow artefacts for audit.

## Operational notes

- Default feature flag for RAG is **off** until operators enable keys and policies.
- Without LLM keys, generation fails gracefully; observability logs still record retrieval.
