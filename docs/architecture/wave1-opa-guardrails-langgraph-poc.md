# Wave 1: OPA, zentrale LLM-Guardrails, LangGraph-PoC

Kurzdokument für die kombinierte Schicht aus Policy-Enforcement, Eingabe-/Ausgabe-Guardrails und dem ersten LangGraph-Workflow.

## OPA (Policy)

- **Module:** `app/policy/` — `opa_client`, `policy_guard`, `role_resolution`, `user_context`.
- **Enforcement:** `enforce_action_policy(...)` in FastAPI-Routen (u. a. Board-Report, Readiness-Explain, Advisor-Mandantenreport, LangGraph-OAMI-PoC).
- **Rollen:** Env-Variablen pro Route (`COMPLIANCEHUB_OPA_ROLE_*`) und optional Header `x-opa-user-role`, wenn `COMPLIANCEHUB_OPA_TRUST_CLIENT_ROLE_HEADER` gesetzt ist.
- **Rego & CI:** `infra/opa/policies/compliancehub/regos/` inkl. `opa test` in GitHub Actions.

## Guardrail-Layer (LLM)

- **`app/llm/context.py`:** `LlmCallContext` — `tenant_id`, `user_role`, `action_name` für Logs und spätere Nachvollziehbarkeit (EU AI Act, Betriebs-Logging).
- **`app/llm/exceptions.py`:** `LLMContractViolation` bei Schema-Verletzung der LLM-JSON-Antwort.
- **`app/llm/guardrails.py`:**
  - `GuardrailScanResult` mit `has_pii`, `has_injection_markers`, `risk_level` (`low` / `medium` / `high`), `flags`.
  - `scan_input_for_pii_and_injection` — Regex (E-Mail, IBAN-ähnlich, Telefon, Injection-Marker). **high** bei PII **und** Injection; **medium** bei PII allein oder **nur** Injection (stärkeres Logging ohne PII); **low** sonst.
  - `log_llm_guardrail_scan` — **medium** und **high** werden immer geloggt (info/warning); low auf debug.
  - `validate_llm_json_output` / `redact_obvious_pii_patterns`.
- **`app/llm/client_wrapped.py`:**
  - `async def safe_llm_call` — Scan, Log, bei **high** Redaktion offensichtlicher PII im Prompt (TODO für HITL/harte Sperre), LLM-Aufruf im Thread-Pool, JSON-Extraktion, Validierung.
  - `safe_llm_call_sync` — gleiche Logik für synchrone Aufrufer (z. B. LangGraph-Knoten).
  - `guardrailed_route_and_call_sync` — für Pfade ohne ein einziges JSON-Schema (Readiness-Explain, Advisor-Brief, Advisor-Executive-Summary).
  - `safe_llm_json_call(...)` — kompatibles Shim mit string-`context` → `action_name`.

## Geschützte LLM-Flows (Wave 1)

| Bereich | Mechanismus |
|--------|-------------|
| Readiness-Score-Explain | `guardrailed_route_and_call_sync` + `LlmCallContext` aus Route (inkl. OPA-Rolle). |
| Advisor Governance-Maturity-Brief | guardrailed Router-Call, Default-Rolle `advisor`; nach Parse **`validate_llm_json_output` → `AdvisorGovernanceMaturityBrief`** (bei Verletzung Fallback). |
| Advisor Executive-Summary (Steckbrief) | guardrailed Router-Call, `response_format` optional. |
| LangGraph OAMI-PoC | Knoten `call_llm` nutzt `safe_llm_call_sync` mit `LlmCallContext`. |

**Hinweis:** `explain_system_oami_de` bleibt **deterministisch ohne LLM**; der PoC nutzt dieselbe Ausgabe-Contract-Klasse `OamiExplanationOut` mit LLM oder deterministischem Fallback.

## LangGraph-PoC (OAMI-Explain)

- **Datei:** `app/agents/langgraph/oami_explain_poc.py`
- **Zustand:** `OamiExplainPocState` (tenant, system, Fenster, Rolle, Index, Prompt, Ergebnis).
- **Knoten (linear + ein Fallback):** `normalize_input` (Index aus DB) → `build_prompt` → `call_llm` (Guardrails + Schema) → bei Vertragsfehler `fallback` (`explain_system_oami_de`) → `post_process` (Validierung `OamiExplanationOut`).
- **Determinismus:** Keine Schleifen; bedingter Zweig nur LLM-Erfolg vs. Fallback.
- **HITL-ready:** Klare Stufen (Policy vor dem Graphen, Scan vor LLM, validierte Ausgabe); TODO in Code für harte Blockierung bei `high` und menschliche Freigabe.
- **Checkpointer:** `MemorySaver` (in-memory).
- **API:**
  - `POST /api/v1/oami-explain-langgraph-poc` — Mandant aus `x-tenant-id` (async, `run_oami_explain_poc_async`).
  - `POST /api/v1/tenants/{tenant_id}/agents/oami-explain-poc` — gleiche Logik mit Pfad-Tenant.
- **Feature-Flag:** `ENABLE_LANGGRAPH_POC`.

## Nicht in dieser Welle

Temporal, Haystack, Postgres-Checkpointer, vollständiges HITL-Produktiv-Deployment der Guardrails.
