# Wave 2: Temporal pilot — AI Compliance Board Report workflow

## Why Temporal

ComplianceHub needs **durable, auditable orchestration** for multi-step processes that combine database reads, optional LLM steps, and persistence. Temporal provides:

- **Deterministic workflow code** (replay-safe) with side effects confined to activities.
- **Durable execution**: retries, visibility, and operational tooling without custom job queues.
- **Clear audit trail**: workflow id / run id can be stored on artefacts and correlated with API audit logs.

This wave introduces **one linear pilot workflow** to establish patterns before broader adoption.

## Pilot workflow: Prepare AI Compliance Board Report

**Goal:** For a tenant, load governance/coverage/OAMI/readiness context, optionally run the **LangGraph OAMI explain PoC** (guardrailed LLM), render the **AI Compliance Board Report** markdown (guardrailed LLM + OPA-aligned action), and persist a **versioned** row in `ai_compliance_board_reports`.

### Components

| Piece | Location |
|--------|-----------|
| Workflow (deterministic) | `app/workflows/board_report.py` — `BoardReportWorkflow` |
| Activities (I/O + LLM) | `app/workflows/board_report_activities.py` |
| Snapshot / persist helpers | `app/services/temporal_board_report.py` |
| Worker process | `app/workflows/worker.py` (`python -m app.workflows.worker`; uses a `ThreadPoolExecutor` for sync activities) |
| FastAPI start + status | `POST /api/v1/tenants/{tenant_id}/board-report/workflows/start`, `GET .../workflows/{workflow_id}` |
| Temporal client (API) | `app/temporal_client.py` |

### Configuration (environment)

| Variable | Purpose |
|----------|---------|
| `TEMPORAL_ADDRESS` | Host:port (default `localhost:7233`) |
| `TEMPORAL_NAMESPACE` | Namespace (default `default`) |
| `TEMPORAL_TASK_QUEUE` | Task queue (default `compliancehub-main`) |
| `TEMPORAL_API_KEY` | Temporal Cloud API key (enables TLS when set) |
| `TEMPORAL_TLS` | Force TLS for local/dev (`1` / `true`) |

### OPA and guardrails

- **Start workflow (API):** action `start_board_report_workflow` (see `infra/opa/policies/compliancehub/regos/action_policy.rego`).
- **LangGraph activity:** `evaluate_action_policy` with action `call_langgraph_oami_explain` before `run_oami_explain_poc` (graph nodes already use `safe_llm_call_sync` + `LlmCallContext`).
- **Persist activity:** `evaluate_action_policy` with action `generate_board_report`, then `render_ai_compliance_board_report_markdown_guardrailed` (`guardrailed_route_and_call_sync` + `LlmCallContext` with `action_name="generate_board_report"`).

No LLM calls run inside the workflow body—only in activities.

### Artefact versioning

Persisted reports set `raw_payload.version` **2** and include `source`, `temporal_workflow_id`, `temporal_run_id`, optional readiness/governance snapshot metadata, and the LangGraph OAMI explanation payload when present.

## Local dev

1. Run Temporal (e.g. [Temporal CLI](https://docs.temporal.io/cli) `temporal server start-dev` or Docker compose).
2. Export `TEMPORAL_ADDRESS` / queue if non-default.
3. Start API (`uvicorn`) and worker: `python -m app.workflows.worker`.

Without a worker, `POST .../workflows/start` will accept the run but executions remain queued until a worker polls the task queue.
