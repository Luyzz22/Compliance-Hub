# Wave 3: Haystack RAG — EU AI Act / NIS2 / ISO 42001 Knowledge Hub (pilot)

## Why Haystack

ComplianceHub needs **retrieval-augmented** answers that are **explainable in audits**: which sources were seen, which model generated the answer, and which policy gates ran. Haystack 2 fits because:

- **Explicit pipeline graphs** (components + `Pipeline.connect`) keep retrieval and prompt construction visible in code, not buried in ad-hoc strings.
- **Swappable document stores** (in-memory for tests, later Postgres + pgvector or managed vector DB) without rewriting business logic.
- Strong adoption in **European** NLP / enterprise search contexts and good fit next to our existing Python stack.

## Pilot scope

- **Use case:** Advisors ask **German** questions about **EU AI Act**, **NIS2**, and **ISO 42001** using a **small curated corpus** under `app/rag/corpus/` (markdown snippets, not full legal texts).
- **Retriever (v1):** `InMemoryBM25Retriever` over `InMemoryDocumentStore` — fast, deterministic in CI, no embedding download.
- **Generator:** `GuardrailedEuRegRagGenerator` calls **`safe_llm_call_sync`** with a Pydantic JSON contract (`EuRegRagLlmOutput`) so **guardrails + LLMRouter** stay aligned with the rest of the platform.
- **API:** `POST /api/v1/advisor/rag/eu-ai-act-nis2-query` with OPA action **`advisor_rag_eu_ai_act_nis2_query`**, headers `x-api-key` + **`x-advisor-id`**, feature flag **`COMPLIANCEHUB_FEATURE_COMPLIANCE_RAG_KNOWLEDGE_HUB`**.

Configuration hints live in `app/rag/haystack_config.py` (e.g. future `COMPLIANCEHUB_RAG_RETRIEVER=embedding` + multilingual sentence-transformers).

## Pipeline graph

Defined in `app/rag/pipelines/eu_ai_act_nis2_pipeline.py`:

1. **Retriever** — BM25 over the in-memory store.
2. **`EuAiActNis2PromptBuilder`** — builds the German compliance prompt and passes through **`retrieved_documents`** (Haystack only returns leaf outputs; this preserves audit context).
3. **`GuardrailedEuRegRagGenerator`** — structured LLM answer + citations.

## Ingestion

`scripts/ingest_eu_ai_act_nis2_corpus.py` loads `.md` files, splits into paragraph chunks with metadata (`source`, `section`, `article`), and writes to an in-memory store (stdout logging). Point `--corpus-dir` at additional curated files when expanding the pilot.

## Integration outlook

- **Temporal (Wave 2):** Long-running advisor or board workflows can call this RAG as an **activity** (same guardrailed generator, same OPA action or a derived one) to pre-answer recurring regulatory questions and attach citations to workflow artefacts.
- **Advisor / board flows:** Responses can be merged into tenant reports or snapshot exports once tenant–advisor linkage and retention policies are applied.

## Operational notes

- Default feature flag for RAG is **off** until operators enable keys and policies.
- Corpus is **global** for the pilot; tenant-specific indexes can follow via metadata filters on the document store and OPA-scoped actions.
