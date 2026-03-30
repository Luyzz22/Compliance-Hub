# Wave 1: OPA, LLM-Guardrails, LangGraph-PoC

Kurzüberblick zur Architektur-Erweiterung (ohne Temporal/Haystack).

## Open Policy Agent (OPA)

- **Zweck:** Zentrale, explizite **Aktionsentscheidungen** (welche Rolle darf welche Operation ausführen, Risiko-Schwellen, globale Denylist) entkoppelt vom Anwendungscode.
- **Python:** `app/policy/opa_client.py` — HTTP-POST gegen `{OPA_URL}{OPA_POLICY_PATH}` mit `{"input": {...}}`; erwartet booleschen `result`.
- **Rego:** `infra/opa/policies/compliancehub/regos/action_policy.rego` — u. a. `generate_board_report`, `call_llm_explain_readiness`, `advisor_tenant_report`, `call_langgraph_oami_explain`; Deny bei `risk_score >= 0.8` ist in den Regeln über `< 0.8` abgebildet; globale Denylist-Einträge `auto_delete_data`, `auto_approve_dsar`.
- **FastAPI:** `app/policy/policy_guard.py` — `enforce_action_policy(...)` wirft bei Verweigerung HTTP **403** (englische API-`detail`-Strings).
- **Hinweis zu `app/security.py`:** Das bestehende Modul `app/security.py` bleibt für API-Key/Tenant-Auth. Policy-Code liegt bewusst unter **`app/policy/`**, um keine Paket-/Modulnamens-Kollision mit `app/security.py` zu erzeugen.

### Umgebungsvariablen

| Variable | Bedeutung |
|----------|-----------|
| `OPA_URL` | Basis-URL des OPA (z. B. `http://localhost:8181`). Leer = Entscheidung **allow** mit Grund `opa_disabled` (lokale Entwicklung). |
| `OPA_POLICY_PATH` | Pfad, Standard `/v1/data/compliancehub/allow_action`. |
| `COMPLIANCEHUB_OPA_STRICT_MISSING` | Wenn `1`/`true` und `OPA_URL` leer: **deny** (`opa_not_configured`) — für Striktheit in Staging/Prod. |
| `COMPLIANCEHUB_OPA_TRUST_CLIENT_ROLE_HEADER` | Wenn `1`/`true`: Header `x-opa-user-role` wird (nach Allowlist) für die Policy verwendet. **Standard aus** — nur aktivieren, wenn das Gateway die Rolle vertrauenswürdig setzt. |
| `COMPLIANCEHUB_OPA_ROLE_BOARD_REPORT` | Logische Rolle für Board-Report-Policy (Allowlist: `advisor`, `tenant_admin`, `tenant_user`, `viewer`). Default im Code: `tenant_admin`. |
| `COMPLIANCEHUB_OPA_ROLE_READINESS_EXPLAIN` | Rolle für Readiness-Explain. Default: `tenant_user`. |
| `COMPLIANCEHUB_OPA_ROLE_LANGGRAPH_OAMI_POC` | Rolle für LangGraph-OAMI-PoC. Default: `tenant_admin`. |
| `COMPLIANCEHUB_OPA_ROLE_ADVISOR_TENANT_REPORT` | Rolle für Advisor-Mandantenreport. Default: `advisor`. |

Auflösung: bei aktivem Trust zuerst **Header** (falls gültig), sonst **Env** (falls gültig), sonst **Default** pro Route (`app/policy/role_resolution.py`).

### CI: Rego-Tests

- Datei `infra/opa/policies/compliancehub/regos/action_policy_test.rego` — `opa test` gegen das Policy-Bundle.
- GitHub Actions: Job `lint-test` installiert OPA (pinned) und führt `opa test infra/opa/policies/compliancehub/regos/` aus.

### Eingebundene Routen (Beispiele)

- `POST .../board/ai-compliance-report` — Aktion `generate_board_report`, Rolle aus Env/Header/Default (Default `tenant_admin`), Risiko ~0.75.
- `POST .../readiness-score/explain` — `call_llm_explain_readiness`, Default-Rolle `tenant_user`, Risiko ~0.45.
- `GET .../advisors/.../tenants/.../report` — `advisor_tenant_report`, Default `advisor`, Risiko ~0.55.
- `POST .../agents/oami-explain-poc` — `call_langgraph_oami_explain`, Default `tenant_admin`, Risiko ~0.4.

Rollen sind **logische** OPA-Rollen bis echtes User-RBAC (JWT/SSO) angebunden ist.

## LLM-Guardrails

- **Modul:** `app/llm/guardrails.py`
  - `scan_input_for_pii_and_injection` — heuristische Regex (E-Mail, IBAN-ähnlich, Telefon, einfache Injection-Marker); liefert `GuardrailScanResult` mit `risk_level` low/medium/high.
  - `validate_llm_json_output` — strikte Pydantic-Validierung; bei Fehler `LLMContractViolation`.
  - `log_input_guardrail_scan` — Logging bei medium/high.
- **Sichere strukturierte Calls:** `app/llm/safe_llm_invoke.py` — `safe_llm_json_call` = Scan → `LLMRouter.route_and_call` → JSON extrahieren → `validate_llm_json_output`.
- **Eingebunden (Logging v1):** Prompts für Readiness-Explain, Advisor-Governance-Maturity-Brief und Advisor-Executive-Summary-Anreicherung werden vor dem LLM-Aufruf gescannt und protokolliert (kein hartes Blocken in dieser Welle).

## LangGraph-PoC (OAMI-Explain)

- **Code:** `app/agents/langgraph/oami_explain_poc.py` — linearer Graph mit bedingtem Zweig: Index laden → guardrailierter LLM-JSON-Call (`OamiExplanationOut`) → bei Vertragsfehler **deterministischer Fallback** (`explain_system_oami_de`).
- **Checkpointer:** `MemorySaver` (minimal, kein Postgres-Checkpointer in Wave 1).
- **API:** `POST /api/v1/tenants/{tenant_id}/agents/oami-explain-poc` — gleiches JSON-Contract wie die bestehende OAMI-Erklärung (`OamiExplanationOut`), synchron, mit OPA-Policy `call_langgraph_oami_explain`.
- **Feature-Flag:** `ENABLE_LANGGRAPH_POC` — wenn nicht `1`/`true`/`yes`/`on`, antwortet der Endpunkt mit **404 Not found** (schrittweise Einführung).

## Nicht in Wave 1

- Temporal, Haystack, Postgres-Checkpointer für LangGraph, vollständiges RBAC aus JWT/SSO.
