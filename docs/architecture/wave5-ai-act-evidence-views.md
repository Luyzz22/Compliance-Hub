# Wave 5: AI Act Evidence Views (read-only API)

## Purpose

Compliance officers and auditors need a **single, tenant-scoped read API** to inspect **AI-related activity** over a time window: regulatory RAG usage, board-report workflows, and LLM guardrail/contract outcomes. This wave is **API-only**; the JSON contracts are stable for a future UI.

## What is surfaced (v1)

| Source | Storage | Event types |
|--------|---------|-------------|
| Advisor EU regulatory RAG | `audit_events` (`entity_type=advisor_regulatory_rag`) | `rag_query` |
| Temporal board-report start | `audit_events` (`entity_type=temporal_board_report_workflow`) | `board_report_workflow_started` |
| Temporal board-report completion | `ai_compliance_board_reports` (`raw_payload.source=temporal_board_report_workflow`) | `board_report_completed` |
| LLM JSON contract failure | `audit_events` (`entity_type=llm_contract_violation`) | `llm_contract_violation` |
| LLM blocked / configuration / provider errors | `audit_events` (`entity_type=llm_guardrail_block`) | `llm_guardrail_block` |

RAG pipeline **structured log lines** (`rag_query_event`) remain in application logs for trace correlation (Wave 4); the **evidence list** uses **audit_events** as the durable sink for RAG completions.

## API

- `GET /api/v1/evidence/ai-act/events` — paginated list (`tenant_id`, `from_ts`, `to_ts`, optional `event_types`, optional `confidence_level` for RAG rows).
- `GET /api/v1/evidence/ai-act/events/{event_id}?tenant_id=` — detail (`audit:…` or `board_report:…`).
- `GET /api/v1/evidence/ai-act/export?tenant_id=&format=csv|json` — same filters as list; **metadata only**.

All routes require API key auth (`x-tenant-id`), feature flag `COMPLIANCEHUB_FEATURE_AI_ACT_EVIDENCE_VIEWS` (default on), and OPA action **`view_ai_evidence`** (roles: `compliance_officer`, `auditor`, `tenant_admin`). Role resolution uses header `x-opa-user-role` or env `COMPLIANCEHUB_OPA_ROLE_AI_EVIDENCE` (default `tenant_admin`).

## EU AI Act / ISO 42001 / NIS2 alignment

- **Transparency and logging:** Evidence rows expose **when** AI-assisted functions ran, **for which tenant**, and **high-level outcome** (e.g. RAG confidence, workflow completion) without storing full prompts or model outputs in the evidence export.
- **Human oversight:** Low-confidence RAG is visible via `confidence_level` and German summaries.
- **Accountability:** LLM contract violations and guardrail-related blocks are persisted as audit events for later review.
- **NIS2 / operational resilience:** Workflow start events and completed report metadata support incident and change-related audits.

## Data minimization

- **No** full questions or answers in list/export/detail for RAG; use **`query_sha256`** and **document IDs** only.
- **No** `rendered_markdown` or prompts in evidence responses.
- Board-report detail lists **activity names** derived from payload keys (e.g. LangGraph explanation present), not content.

## Implementation notes

- Read model: `app/evidence/queries.py` aggregates `audit_events` + board report rows; **no dedicated evidence table** in v1.
- LLM failures: `app/evidence/llm_audit.py` is invoked from `app/llm/client_wrapped.py` when a `Session` is available.
