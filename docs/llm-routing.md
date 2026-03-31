# LLM-Routing in Compliance Hub

Enterprise-Router für mandantenfähige Modellwahl (Qualität, Kosten, Datenschutz) mit Feature-Flags und Metadaten-Logging **ohne** Speicherung von Prompt- oder Response-Inhalten.

## Task-Typen (`LLMTaskType`)

| Task | Typische Nutzung | Standard-Präferenz (wenn Policy nichts anderes vorgibt) |
|------|------------------|---------------------------------------------------------|
| `legal_reasoning` | Norm-Mapping, Art.-Analysen, Audit-Texte | Claude, dann OpenAI |
| `structured_output` | JSON/Markdown, Reports, Exporte | OpenAI (GPT-4o), dann Claude |
| `classification_tagging` | Kategorien, Stichworte, Heuristiken | Gemini, dann OpenAI |
| `chat_assistant` | Interaktive UI-Hilfe | OpenAI, dann Claude |
| `embedding_retrieval` | RAG-Embeddings | Llama (on-prem), dann OpenAI Embeddings |
| `on_prem_sensitive` | Daten ohne Public-Internet | **nur** Llama; Fehler ohne `LLAMA_BASE_URL` |

Bei `cost_sensitivity=high` oder `latency_sensitivity=high` werden für `classification_tagging` und `chat_assistant` Gemini bevorzugt.

## Provider (`LLMProvider`)

- `claude` – Anthropic Messages API (`CLAUDE_API_KEY` oder `ANTHROPIC_API_KEY`)
- `openai` – Chat Completions / Embeddings (`OPENAI_API_KEY`, optional `OPENAI_BASE_URL`)
- `gemini` – Google Generative Language API (`GEMINI_API_KEY` oder `GOOGLE_API_KEY`)
- `llama` – OpenAI-kompatibler Endpunkt (`LLAMA_BASE_URL`, optional `LLAMA_API_KEY`)

Modelle (überschreibbar): `COMPLIANCEHUB_CLAUDE_MODEL`, `COMPLIANCEHUB_OPENAI_MODEL`, `COMPLIANCEHUB_GEMINI_MODEL`, `COMPLIANCEHUB_LLAMA_MODEL`, `COMPLIANCEHUB_OPENAI_EMBEDDING_MODEL`, `COMPLIANCEHUB_LLAMA_EMBEDDING_MODEL`.

## Mandanten-Policy (`TenantLLMPolicy`)

Felder (Auszug):

- `allowed_providers` – erlaubte Provider
- `default_provider_by_task` – Override der Standardkette pro Task
- `require_on_prem_for_sensitive` – wenn `true`, wird `legal_reasoning` mit Llama **zuerst** versucht
- `cost_sensitivity` / `latency_sensitivity` – `low` | `medium` | `high`
- `data_residency` – `us_cloud_allowed` | `eu_only`
- `public_api_policy` – `public_api_allowed` | `on_prem_only`

### Konfiguration

1. **Standard** – alle Provider erlaubt (siehe `app/services/tenant_llm_policy.py`).
2. **ENV-Map** – `COMPLIANCEHUB_LLM_TENANT_POLICIES_JSON`: JSON-Objekt `{ "<tenant_id>": { ...partial policy... } }` (deep-merge mit Standard).
3. **Datenbank** – Tabelle `tenant_llm_policy_overrides`: Spalte `policy_json` (Partial-JSON, gleiches Merge-Verhalten), wenn eine `Session` an `get_tenant_llm_policy` übergeben wird.

## Datenschutz / Region (Annahmen)

- `eu_only`: Ohne weitere Freigabe werden nur **Llama**-Routen genutzt (on-prem unter Ihrer Kontrolle).
- Optional: `COMPLIANCEHUB_LLM_ASSUME_CLAUDE_EU=true` – Betreiber bestätigt EU-konforme Claude-Verarbeitung.
- Optional: `COMPLIANCEHUB_LLM_US_CLOUD_OK=true` – Betreiber bestätigt zulässige Nutzung von US-SaaS-APIs (OpenAI/Gemini) trotz `eu_only` (z. B. eigene EU-Residency-Verträge).

`public_api_policy=on_prem_only` erlaubt nur noch **Llama** (sofern konfiguriert).

## Feature-Flags

Backend (`COMPLIANCEHUB_FEATURE_*`, Standard siehe `app/feature_flags.py`):

- `COMPLIANCEHUB_FEATURE_LLM_ENABLED` – **Standard: aus** (`false`)
- `COMPLIANCEHUB_FEATURE_LLM_LEGAL_REASONING`
- `COMPLIANCEHUB_FEATURE_LLM_REPORT_ASSISTANT` (u. a. strukturierte Outputs / Advisor-Summary)
- `COMPLIANCEHUB_FEATURE_LLM_CLASSIFICATION_TAGGING`
- `COMPLIANCEHUB_FEATURE_LLM_CHAT_ASSISTANT`
- `COMPLIANCEHUB_FEATURE_AI_ACT_DOCS` – EU-AI-Act-Dokumentations-UI/API (ohne LLM-Pflicht)
- `COMPLIANCEHUB_FEATURE_WHAT_IF_SIMULATOR` – Board-What-if (reine Rechenlogik, kein LLM)

**KI-Entwürfe für AI-Act-Sektionen** (`POST .../ai-act-docs/.../draft`): zusätzlich `LLM_LEGAL_REASONING` + `LLM_REPORT_ASSISTANT` (zweistufig: Analyse, dann JSON/Markdown).

Frontend-Hinweis: `NEXT_PUBLIC_FEATURE_LLM_ENABLED` (Standard aus), `NEXT_PUBLIC_FEATURE_AI_ACT_DOCS`, `NEXT_PUBLIC_FEATURE_WHAT_IF_SIMULATOR`, optional `NEXT_PUBLIC_FEATURE_LLM_LEGAL_REASONING` / `NEXT_PUBLIC_FEATURE_LLM_REPORT_ASSISTANT` für Draft-Buttons.

## API

- `POST /api/v1/llm/invoke` – Body `{ "task_type": "<LLMTaskType>", "prompt": "..." }`, Mandanten-Auth wie üblich. Erfordert `llm_enabled` und das jeweilige Task-Flag.

## Observability

- Tabelle `llm_call_metadata`: `tenant_id`, `task_type`, `provider`, `model_id`, Längen, Latenz, Token-Schätzungen – **keine** Inhalte.
- Usage-Metriken (`GET .../usage-metrics`): `llm_calls_last_30d` und Aufschlüsselung nach Task-Typ.

## Integration im Produktcode

- Router: `LLMRouter(session=...).route_and_call(task_type, prompt, tenant_id, **kwargs)`
- Hooks: `app/services/llm_compliance_tasks.py` (Legal/Structured/Classification-Assist)
- Advisor-Steckbrief: optional `executive_summary_narrative` aus denselben Kennzahlen (Feature `llm_report_assistant`)

Die deterministische EU-AI-Act-Klassifikation (`classification_engine`) bleibt unverändert; LLM liefert höchstens ergänzende Textvorschläge.
