# Governance-Maturity: Copy- und API-Vertrag (Backend ↔ Frontend)

Ziel: **gleiche Fachbegriffe** und **stabile API-Enums** für Readiness, GAI und OAMI; **deutsche Labels** kommen primär aus dem Frontend-Copy-Modul, das Backend liefert **strukturierte Inhalte** (Gründe, Maßnahmen) und **API-Level-Strings**.

## 1. API-Level (sprachneutral)

| Konzept | API-Werte (`level`) | Deutsche UI-Labels (nur Frontend) |
|--------|----------------------|-------------------------------------|
| AI & Compliance Readiness | `basic`, `managed`, `embedded` | Basis, Etabliert, Integriert |
| Governance-Aktivität (GAI) | `low`, `medium`, `high` | Niedrig, Mittel, Hoch |
| Operatives KI-Monitoring (OAMI) | `low`, `medium`, `high` | Niedrig, Mittel, Hoch |

**Backend (Python):** `app/governance_maturity_contract.py` — `ReadinessLevelApi`, `GovernanceActivityLevelApi`, `OperationalMonitoringLevelApi`, Normalisierer `normalize_readiness_level` / `normalize_index_level`.

**Frontend (TypeScript):** `frontend/src/lib/governanceMaturityTypes.ts` — dieselben String-Unions.

**Deutsche Texte / Tooltips:** ausschließlich `frontend/src/lib/governanceMaturityDeCopy.ts` (siehe auch `docs/governance-maturity-copy-de.md`).

## 2. LLM Readiness-Explain (`POST .../readiness-score/explain`)

- **Prompt:** `terminology_contract_for_llm_prompt()` + `readiness_explain_json_schema_instructions()` in `app/governance_maturity_contract.py`; Implementierung in `app/services/readiness_score_explain.py`.
- **Erwartetes Modell-Output:** ein JSON-Objekt (ohne Markdown) mit:
  - `readiness_explanation`: `score`, `level` (API!), `short_reason`, `drivers_positive`, `drivers_negative`, `regulatory_focus`
  - `operational_monitoring_explanation`: optional / `null` — `index`, `level` (API!), `recent_incidents_summary`, `monitoring_gaps`, `improvement_suggestions`
- **Validierung:** `app/services/readiness_explain_structured.py` parst JSON, clamped Listen, **erzwingt `readiness.score`/`readiness.level` aus dem Server-Snapshot** (kein Drift).
- **Antwort:** `ReadinessScoreExplainResponse` (`app/readiness_score_models.py`):
  - `explanation` — zusammengesetzter Fließtext für Legacy-UI
  - `readiness_explanation` / `operational_monitoring_explanation` — optional strukturiert für Board-UI

`response_format=json_object` wird an OpenAI durchgereicht; andere Provider liefern ggf. Text — Parser toleriert Codefences und extrahiert `{...}`.

## 3. Frontend-Konsum

- **Labels:** immer `governanceMaturityDeCopy` + `getReadinessCopy` / `getActivityCopy` / `getMonitoringCopy` anhand der **API-Levels** aus dem Score/Snapshot/API.
- **KI-Text:** `short_reason`, `drivers_*`, `regulatory_focus`, OAMI-Felder aus der API anzeigen; **keine** parallelen Level-Strings im UI erfinden, wenn strukturierte `level`-Felder gesetzt sind.
- **Typen:** `frontend/src/lib/api.ts` — DTOs zu `ReadinessScoreExplainResponse` (strukturierte Felder optional).

Demo-Script: `docs/demo-board-ready-walkthrough.md`.

## 4. Tests / Guardrails

- `tests/test_governance_maturity_contract.py` — Terminologie-Strings und Enum-Mengen.
- `tests/test_readiness_explain_structured.py` — JSON-Parsing, Level-Normalisierung, Ausrichtung an Snapshot.

Bei neuen Stufen: **Frontend-Typen, `governanceMaturityDeCopy`, `governance_maturity_contract` und Pydantic-Models** gemeinsam erweitern; LLM-Schema-String in `readiness_explain_json_schema_instructions()` anpassen.
