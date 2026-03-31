# Wave 4: Cross-cutting observability (OpenTelemetry traces + structured logs)

## Goals

- **End-to-end traceability** from HTTP through advisor RAG, Temporal board-report flows, and guardrailed LLM calls.
- **Audit-friendly signals** for EU AI Act, ISO 42001, and NIS2 logging and monitoring (who/what/when, model metadata, outcomes — **no** raw prompts or completions in traces).
- **Join logs and traces** via `trace_id` / `span_id` on normalized events (e.g. `rag_query_event`).

## Components

| Piece | Location | Role |
|--------|-----------|------|
| Tracer setup | `app/telemetry/tracing.py` | `configure_telemetry()`, `start_span`, `record_event`, W3C `inject` / `attach_trace_carrier` |
| HTTP root span | `app/telemetry/middleware.py` | `TelemetryMiddleware`: reads `traceparent`, sets `http.*`, `tenant_id` (from `x-tenant-id`), `user_role`, `correlation_id`; echoes `X-Correlation-ID` |
| RAG | `app/rag/service.py`, `app/rag/pipelines/eu_ai_act_nis2_pipeline.py` | Spans: `rag.query_received`, `rag.retrieval`, `rag.generation`; `log_rag_query_event` adds `trace_id` / `span_id` when a span is active |
| LLM | `app/llm/client_wrapped.py`, `app/services/llm_router.py` | Span `llm.guardrailed_call` with `llm_*` attributes; router adds provider/model/tokens/response length on success |
| Temporal board report | `app/main.py`, `app/workflows/board_report.py`, `app/workflows/board_report_activities.py` | API injects `otel_trace_carrier` into `BoardReportWorkflowInput`; activities `attach_trace_carrier` and emit `activity.load_snapshot`, `activity.langgraph_explain`, `activity.persist_board_report` |

## Trace model (how requests stitch)

1. **Browser / API gateway** may send W3C `traceparent` (optional). Middleware continues that trace or starts a new one.
2. **Advisor RAG** (`POST /api/v1/advisor/rag/eu-ai-act-nis2-query`): HTTP span → `rag.query_received` → `rag.retrieval` → (optional) `rag.generation` → nested `llm.guardrailed_call` when the LLM runs.
3. **Board report workflow start** (`POST .../board-report/workflows/start`): HTTP span → `temporal.board_report.enqueue` → `inject_trace_carrier` captures the **current** span context into `otel_trace_carrier` passed to Temporal. Worker activities **extract** that context so their spans share the **same `trace_id`** as the API call.
4. **Workflow body** (`BoardReportWorkflow`) intentionally has **no** OpenTelemetry calls (Temporal replay / determinism). Logical “workflow” visibility is covered by the enqueue span plus activity spans.

## Environment

| Variable | Purpose |
|----------|---------|
| `COMPLIANCEHUB_OTEL_ENABLED` | Default on; set `false` to skip registering `TracerProvider` (no-op tracing). |
| `COMPLIANCEHUB_OTEL_SERVICE_NAME` | Default `compliancehub-api`. |
| `COMPLIANCEHUB_ENVIRONMENT` | `dev` / `stage` / `prod` (resource attribute). |
| `COMPLIANCEHUB_OTEL_CONSOLE_EXPORTER` | `1` enables `ConsoleSpanExporter` (local debugging only). |

Production typically attaches an OTLP exporter via the OpenTelemetry SDK (not hard-coded here) so Jaeger / Grafana / the OTEL Collector can be swapped without app changes.

## Example analytics queries (conceptual)

These are **documentation targets** for your log/trace backend (not shipped SQL).

1. **Low-confidence RAG answers for a tenant (last 7 days)**  
   Filter structured logs: `event=rag_query`, `phase=response_complete`, `confidence_level=low`, `tenant_id=<id>`, time range. Use `trace_id` to open the full trace (retrieval scores, LLM span outcome).

2. **Board report workflows with LLM contract violations**  
   Filter traces/spans where `llm_result=contract_violation` and parent or linked attributes include `workflow_id` / `tenant_id` (from enqueue or activity spans). Correlate with Temporal workflow ID from audit logs.

3. **End-to-end latency**  
   Trace: `http ...` → `rag.*` → `llm.guardrailed_call` or `temporal.board_report.enqueue` → `activity.*` → `llm.guardrailed_call`.

## EU AI Act / ISO 42001 / NIS2 alignment (high level)

- **Technical documentation and logs** of high-risk AI operations benefit from consistent **trace identifiers** and **outcome metadata** (e.g. `llm_result`, RAG `confidence_level`) without storing **content** of prompts or answers in traces.
- **Human oversight**: low-confidence RAG paths remain explicit in logs (`confidence_level`, `notes_de` in the API); traces link to the same request for incident review.
- **Monitoring**: rate of `guardrail_blocked`, `contract_violation`, and provider errors supports operational and governance KPIs.

## Privacy

- **Never** log full prompts or completions in span attributes or `record_event` payloads; use **lengths**, **hashes** (e.g. `llm_prompt_sha256_prefix`), and **enumerated results** only.
- RAG logs keep **query SHA-256** and **redacted previews** (existing Wave 3 behavior); trace IDs are appended for correlation.
