# Governance Workflows (Developer-DX)

Kurzüberblick für die deterministische Workflow-Orchestration (Tasks, Runs, Events, UI).

## Task-Status (API-Modell)

- **Erlaubte Werte (PATCH):** `open` · `in_progress` · `done` · `cancelled` · `escalated` (Pydantic `Literal`, gleiche Quelle im Backend-ORM).
- **Semantik (MVP):** `open` = noch nicht in Bearbeitung, `in_progress` = Bearbeitung läuft, `done` / `cancelled` = **Endzustand**, `escalated` = fachlich eskaliert, oft mit höherer Eskalationsstufe/Visibility.
- **Hinweis UI:** Begriffe wie `blocked` oder `deferred` erscheinen in der Produktsprache ggf. als Anzeige-Label – in der **API** werden sie nicht persistiert, sondern über einen der fünf erlaubten Stati abgebildet.
- **Übergänge (Client-Guard, nicht API-Zwang im MVP):** In der Web-App werden Wechsel von `done` / `cancelled` zu jedem **anderen** Status unterbunden, um fälschliches „Wiederöffnen“ im UI zu verhindern; ein bewusstes Re-Open wäre eine API-/Prozess-Erweiterung.

## Zuweisung entfernen (Unassign)

- **Client:** `PATCH /api/v1/governance/workflows/tasks/{id}` mit JSON-Body `{"assignee_user_id": null}` (explizit `null`, kein leeres String-Literal – das Feld ist optional/nullable).
- **Semantik:** `null` bedeutet *nicht zugewiesen*; ein gesetzter String ist die Mandanten-interne User- oder Owner-ID.
- **Tests:** `tests/test_governance_workflow_api.py` deckt `assignee_user_id: None` (Python) bzw. JSON-`null` ab.

## Neue Quellen, `dedupe_key` und `RULE_BUNDLE_VERSION`

- **Neue `source_type`-Werte:** 1) Materialisierung in `app/services/governance_workflow_service.py` (Konsistenz der Objekt-Referenz/Join), 2) ggf. Literal/Erweiterung in Pydantic, 3) `WORKFLOW_SOURCE_TYPE_VALUES` in `frontend/src/lib/governanceWorkflowTypes.ts` und **Filter-Option** in der Governance-Workflow-UI, 4) sinnvolles Mapping in `governance_workflow` Events/Payload, falls sichtbar.
- **`dedupe_key` (pro Tenant):** Stabil pro fachlichem Ereignis, damit derselbe Regel-Run keine Task-Duplikate erzeugt (siehe `_materialize`-Hilfsfunktionen: gleiches „Sinnes-Objekt“ → gleiche Schlüssel-Strategie). Bei neuen Quellen dieselbe disziplinierte Schlüsseldefinition verwenden.
- **`RULE_BUNDLE_VERSION`:** Konstante im Service; jede inhaltlich relevante Regel-Änderung hochzählen, damit **Runs, Audit-Trail und `recent_runs`** die verwendete Regelversion pro Lauf anzeigen und Regressionen eingeordnet werden können.

## `events_written` / Event-KPIs

- **`events_written`:** Lauf-Metrik, wie viele `governance_workflow_events` **während** dieses `run_deterministic_sync` geschrieben wurden (Tally im Regel-Loop, nicht 24h-Gesamt).
- **Ort in der API:** Sichtbar im **Body von `POST .../workflows/run`** (Response) und in **`summary.events_written` der Run-Zeile** (Dashboard-`recent_runs` → Feld `summary`).
- **Einsatz:** Operatives Monitoring (Spike nach Rule-Bundle-Change), Korrelation mit `tasks_materialized` im `summary`, Board-/Tenant-Dashboard-„Ereignisse pro Sync“.
- **24h-Events:** `kpis.workflow_events_24h` bezieht sich rollierend auf die Tabelle, nicht auf einen einzelnen Lauf (semantische Differenz zu `events_written`).

## Tests

- `tests/test_governance_workflow_api.py`: u. a. 422 bei ungültigem `status` für `PATCH /tasks/...`, explizites `assignee_user_id: null`, `POST /run` mit `events_written` ≥ 0.
