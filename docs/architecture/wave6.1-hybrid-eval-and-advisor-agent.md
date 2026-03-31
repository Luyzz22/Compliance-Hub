# Wave 6.1 — Hybrid Retrieval Evaluation & Advisor LangGraph Agent

## Overview

Wave 6.1 combines two complementary workstreams:

1. **Part A**: Offline evaluation of BM25 vs. hybrid (BM25 + dense) retrieval for compliance advisor queries, including score fusion tuning and confidence calibration.
2. **Part B**: A LangGraph-style Advisor Agent (`AdvisorComplianceAgent`) that orchestrates RAG retrieval, answer synthesis, and human escalation in a controlled, auditable graph.

Both are designed for auditability under **EU AI Act** (Art. 13 transparency, Art. 9 risk management) and **ISO 42001** (A.6.2.6 AI risk assessment).

---

## Part A — Hybrid Retrieval Evaluation

### Evaluation Approach

- **Ground truth**: Curated YAML file (`data/eval/ground_truth.yaml`) with synthetic queries mapped to expected corpus documents. No raw customer prompts — only category-based representative queries (e.g. "Hochrisiko-Systeme Definition", "NIS2 Meldefrist").
- **Corpus**: Synthetic regulatory documents covering EU AI Act, NIS2, ISO 42001, and DSGVO — mirrors production corpus structure.
- **Script**: `scripts/rag_eval_hybrid.py` runs BM25-only and hybrid retrieval (no LLM calls) and computes:
  - **Recall@k** against expected doc_ids
  - **Precision@k** against expected doc_ids
  - **NDCG@k** for ranking quality
- Outputs CSV and JSON with per-query and aggregated metrics.

### Score Fusion Formula

```
combined_score = (1 - α) · BM25_normalized + α · dense_score
```

Where:
- `α` = `HYBRID_ALPHA` (configurable, default **0.30**)
- BM25 scores are min-max normalized per query
- Dense scores are cosine similarities (already 0–1)

### Chosen Fusion Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `HYBRID_ALPHA` | 0.30 | Conservative bias toward BM25 to reduce hallucination risk. Dense complements BM25 on semantic near-misses. |
| `BM25_FLOOR` | 0.10 | Documents below this BM25 score are excluded even if dense scores highly — prevents dense-only hallucinations on out-of-corpus queries. |
| `DENSE_THRESHOLD` | 0.25 | Minimum dense cosine similarity for a document to be a "rescue" candidate. |

Parameters are set via environment variables (`COMPLIANCEHUB_HYBRID_ALPHA`, `COMPLIANCEHUB_BM25_FLOOR`, `COMPLIANCEHUB_DENSE_THRESHOLD`) or in `app/services/rag/config.py`.

### Confidence Heuristic

```
HIGH:   combined_score ≥ 0.65 AND bm25_score ≥ 0.25
MEDIUM: combined_score ≥ 0.35 AND bm25_score ≥ 0.10
LOW:    otherwise

Boost: If gap between rank-1 and rank-2 scores ≥ 0.15 → medium→high
```

The BM25 floor in the confidence check ensures the system never auto-answers based solely on dense similarity without any term-level evidence.

### Fallback Logic

When the system declines to answer ("no match"):
1. Check if **any** result passes the BM25 floor → if not, decline.
2. Check combined confidence → if "low", recommend human review.
3. Log the decline event with retrieval scores for audit.

---

## Part B — Advisor LangGraph Agent

### Graph Design

```
START → classify_intent
            │
    ┌───────┼───────┐
    ▼       ▼       ▼
run_rag  escalate  END (out_of_scope)
    │
    ▼
check_confidence
    │
  ┌─┴──┐
  ▼    ▼
synth  escalate
  │    │
  ▼    ▼
 END  END
```

**Nodes:**

| Node | Type | Description |
|------|------|-------------|
| `classify_intent` | Rule-based | Keyword classifier: informational / action_oriented / out_of_scope |
| `run_rag_query` | Retrieval | Calls HybridRetriever with configured mode |
| `check_confidence` | Policy gate | Routes to synthesize or escalate based on confidence + tenant guidance policy |
| `synthesize_answer` | LLM | Generates structured German advisory via `safe_llm_call_sync` |
| `escalate_to_human` | Terminal | Flags query for human review |

**Key design choices:**
- **Small, explicit graph** — no self-modifying loops or unbounded tool calls.
- **Conservative**: bei Unsicherheit → "menschliche Prüfung empfohlen".
- **All LLM nodes** use `safe_llm_call_sync` with `LlmCallContext` (tenant_id, role, action).

### Guardrails & Policies

1. **LLM guardrails**: All calls go through `safe_llm_call_sync` which enforces error handling and audit logging.
2. **Escalation policies**:
   - `confidence_level == "low"` → force escalation
   - Tenant has guidance docs but retrieval returned only global law → force escalation
3. **Prompt guardrails**: The `build_rag_prompt` function enforces German language, citation requirements, and no-speculation rules.

### Agent State & Audit Trail

Every node execution is appended to `AdvisorState.agent_trace` — an ordered list of decisions:

```json
[
  {"node": "classify_intent", "intent": "informational"},
  {"node": "run_rag_query", "retrieval_mode": "hybrid", "confidence_level": "high", ...},
  {"node": "synthesize_answer", "status": "success", "model_id": "claude-sonnet-4", ...}
]
```

This trace is surfaced in AI Act evidence views and can be queried for compliance audits.

---

## Observability & AI Act Evidence

### RAG Audit Logging

Every RAG query emits a structured `RAGQueryEvent` via `log_rag_query_event()`:

| Field | Description |
|-------|-------------|
| `query_hash` | SHA-256 hash of query (no PII) |
| `retrieval_mode` | "bm25" or "hybrid" |
| `alpha_used` | Fusion alpha value |
| `confidence_level` | "high" / "medium" / "low" |
| `top_doc_ids` | Retrieved document IDs |
| `top_rescue_sources` | "bm25", "dense", or "both" per doc |
| `hybrid_changed_top_doc` | Whether hybrid reranked the top doc |
| `agent_action` | Agent decision (e.g. "synthesize_answer", "escalate") |

### Suggested Dashboard Queries

1. **Hybrid rescue rate**: Percentage of queries where hybrid changed the top doc vs. BM25:
   ```
   COUNT(hybrid_changed_top_doc=true) / COUNT(*) WHERE retrieval_mode='hybrid'
   ```

2. **Escalation rate**: Percentage of queries escalated to human:
   ```
   COUNT(agent_action='escalate_to_human') / COUNT(*)
   ```

3. **Confidence distribution**:
   ```
   GROUP BY confidence_level → COUNT(*)
   ```

4. **Dense rescue source breakdown**:
   ```
   GROUP BY top_rescue_sources[0] → COUNT(*)
   ```

---

## Temporal Integration (Optional)

The `AdvisorActivityInput`/`AdvisorActivityOutput` pair wraps the agent for Temporal workflows:

- **Activity**: `run_advisor_compliance_agent` — all non-deterministic work (LLM, retrieval) happens inside this activity boundary.
- **Determinism**: The workflow itself only calls this activity; LLM calls never happen in workflow code.
- **Trace propagation**: `trace_id` is passed through `AdvisorActivityInput` so LangGraph agent spans join existing OTel traces.

---

## File Map

| File | Purpose |
|------|---------|
| `app/services/rag/config.py` | RAG configuration (alpha, thresholds, model) |
| `app/services/rag/corpus.py` | Document and RetrievalResult models |
| `app/services/rag/bm25_retriever.py` | BM25 in-memory index |
| `app/services/rag/dense_retriever.py` | Optional dense (embedding) retriever |
| `app/services/rag/hybrid_retriever.py` | Hybrid fusion retriever |
| `app/services/rag/confidence.py` | Confidence heuristic |
| `app/services/rag/logging.py` | Structured RAG audit logging |
| `app/services/rag/llm.py` | Guardrailed LLM call wrappers |
| `app/services/rag/prompt_builder.py` | Prompt construction with guardrails |
| `app/services/agents/advisor_compliance_agent.py` | Advisor agent graph |
| `app/services/agents/temporal_activity.py` | Temporal activity wrapper |
| `data/eval/ground_truth.yaml` | Curated evaluation ground truth |
| `scripts/rag_eval_hybrid.py` | Offline evaluation script |
| `tests/test_rag_eval.py` | Tests for retrieval + evaluation metrics |
| `tests/test_advisor_agent.py` | Tests for advisor agent graph paths |
