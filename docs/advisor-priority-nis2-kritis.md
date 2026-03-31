# Berater-Priorität: NIS2, KRITIS und Incident-Signale

Erweiterung der **regelbasierten** `advisor_priority` im Mandanten-Portfolio. Ziel: bei wesentlichen/wichtigen Einrichtungen, KRITIS-Sektoren und jüngerer Incident-Last **eine Stufe** nachvollziehbar anheben – ohne versteckte Gewichtung oder PII in der API.

## Stammdaten (Quelle)

| Feld (API) | Quelle | Hinweis |
|------------|--------|---------|
| `nis2_entity_category` | `tenants.nis2_scope` normalisiert | `none` / `important_entity` / `essential_entity` |
| `kritis_sector_key` | `tenants.kritis_sector` | Optional; Sektorschlüssel (z. B. `energy`, `health`), keine weiteren Details |
| `recent_incidents_90d` | Zähler Incidents | `true`, wenn mindestens ein Eintrag in **90 Tagen** |
| `incident_burden_level` | Zähler 90 Tage | `low` / `medium` / `high` aus Anzahl und Schwere **high** |

### Normalisierung `nis2_scope` → `nis2_entity_category`

- `none`, `out_of_scope`, … → `none`
- `essential_entity`, `kritis_operator`, … → `essential_entity`
- `important_entity`, Legacy **`in_scope`** → `important_entity`

Provisioning: optional `kritis_sector` im Body von `POST /api/v1/tenants/provision`.

**Schema:** Die Spalte `tenants.kritis_sector` wird bei API-Start bzw. über `python scripts/migrate_all.py` idempotent nachgezogen (siehe `docs/db-migrations.md`). Ohne Migration schlagen Lese-/Schreibzugriffe auf älteren Datenbanken fehl.

## Incident-Last (90 Tage)

- **low:** keine Vorfälle im Fenster
- **medium:** mindestens ein Vorfall
- **high:** ≥ 5 Vorfälle **oder** ≥ 2 mit Schwere `high`

Es werden **keine** Titel, Akteure oder Freitexte aus Incidents exportiert.

## Regeln für den regulatorischen Aufstock (max. eine Stufe)

Voraussetzung **A** (Reife-Stress):

- Readiness nicht `embedded` **oder**
- OAMI fehlt / nicht `high` (fehlendes OAMI zählt vorsichtig als „nicht high“).

Dann mindestens eine der Bedingungen **B**:

1. `nis2_entity_category == essential_entity`
2. `kritis_sector_key` ist gesetzt (Sektor erfasst)
3. `recent_incidents_90d` und `incident_burden_level` ∈ {`medium`, `high`}

Wenn **A** und **B** zutreffen: Priorität **eine Stufe anheben** (`low`→`medium`, `medium`→`high`; `high` bleibt).

Der Tooltip-Text (`advisor_priority_explanation_de`) erhält einen kurzen Satz **Regulatorischer Aufstock (…)**, der die auslösenden **Kategorien** nennt, keine Inhalte aus Vorfällen.

## Beispiele

1. **Wesentliche Einrichtung, schwaches Monitoring:** `essential_entity`, Readiness `managed`, OAMI `low` → Aufstock um eine Stufe gegenüber reinem Reife-Score.
2. **KRITIS Energie, mittlere Readiness:** `kritis_sector_key=energy`, OAMI `medium` → Aufstock (Sektor + Stress).
3. **Wichtige Einrichtung ohne Vorfälle, gute Reife:** `important_entity`, embedded + OAMI high → **kein** Aufstock (nur NIS2-Badge in der UI).
4. **Kein NIS2/KRITIS, aber Last und Lücken:** `none`, aber 3 Vorfälle in 90 Tagen (`burden` mindestens medium), Readiness `basic` → Aufstock über Incident-Regel.

## CSV / JSON

Export-Spalten u. a.: `nis2_entity_category`, `kritis_sector_key`, `recent_incidents_90d`, `incident_burden_level`, plus bestehende Prioritäts- und Reife-Felder.

## Mandanten-Steckbrief (Markdown)

Der Abschnitt **„Risiko- und Incident-Lage (NIS2/KRITIS)“** im Markdown-Report (`GET …/report?format=markdown`) ist **template-basiert** und nutzt:

- `risiko_nis2_scope_label_de`, `risiko_kritis_sector_label_de` (Stammdaten),
- Zähler 90 Tage und `risiko_incident_burden_level`, offene Vorfälle (Aggregat),
- optional `risiko_regulatory_priority_note_de` (derselbe erklärende Zusatz wie beim Portfolio-Aufstock).

Es werden **keine** Inhalte aus Einzelvorfällen ausgegeben. Goldens: `tests/fixtures/advisor-tenant-report-markdown/risiko-incident-lage/`.

**LLM:** Die optionale Executive Summary (`executive_summary_narrative`) erhält die Risiko-Felder zusätzlich im Fakten-JSON (`advisor_report_llm_enrichment`), damit Formulierungen ohne neue erfundene Zahlen möglich sind. Der Risiko-Abschnitt selbst bleibt deterministisch.

### Gesprächshilfen für Mandantengespräche

- *„Wir klassifizieren eure Einordnung nach NIS2 aus den Stammdaten; im Report seht ihr die aggregierte Incident-Last der letzten 90 Tage ohne Details zu Einzelfällen.“*
- *„Wenn das Berater-Portfolio einen regulatorischen Aufstock gesetzt hat, steht derselbe Hinweis im Steckbrief unter ‚Berater-Portfolio (Priorität)‘ – das ist bewusst konsistent mit eurer Mandantenliste.“*

## Verwandte Dokumente

- [advisor-portfolio-prioritization.md](./advisor-portfolio-prioritization.md) – Basispriorität und Filter
- Code: `app/services/advisor_portfolio_priority.py`, `app/services/advisor_portfolio.py`
