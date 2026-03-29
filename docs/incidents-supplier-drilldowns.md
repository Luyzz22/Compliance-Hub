# Incident-Drilldown: KI-System und Lieferant (Laufzeit)

## Zweck

Der **Incident-Drilldown** fasst **Laufzeit-Incidents** (`event_type=incident` in `ai_runtime_events`) **pro KI-System** und **dominanter Event-Quelle** (`source`, z. B. `sap_ai_core`) im wählbaren Fenster (Standard **90 Tage**) zusammen. Er richtet sich an **Berater** und **interne** Nutzer mit Mandanten-API-Key – nicht an anonyme Endnutzer.

## Inhalt (Aggregation)

- **Zähler** pro Subtyp-Kategorie (**Sicherheit**, **Verfügbarkeit**, **Sonstige**) – gleiche Taxonomie wie OAMI/Board (`incident_subtype_oami_category` in `app/oami_subtype_weights.py`).
- **Gewichtete Anteile** pro Kategorie auf Basis von `incident_subtype_oami_weight` (wie beim Board-Subtype-Profil, ohne Rohkoeffizienten in der API zu erklären).
- **Lieferant / Quelle:** dominanter `source`-Wert im Fenster (häufigster bei Gleichstand lexikographisch stabiler Tie-Break).
- **`oami_local_hint_de`:** ein kurzer deutscher Satz (Safety-/Availability-Fokus, ausgewogen, wenige Fälle).

Keine Roh-Payloads von Prompts/Outputs, keine personenbezogenen Freitexte – nur technische Aggregationen.

## Bezug zu OAMI und Board

| Ebene | Artefakt |
|-------|-----------|
| Mandant | `TenantOperationalMonitoringIndexOut`, Board **OAMI-Subtype-Profil** (gewichtete Anteile über alle Systeme) |
| System | **Incident-Drilldown**-Zeilen je `ai_system_id` |

Der Drilldown beantwortet: *Welches System und welche Anbindung (Quelle) trägt zu Incidents bei?* Das Board-Profil bleibt die **komprimierte Mandanten-Sicht**.

## API

| Methode | Pfad | Auth |
|---------|------|------|
| `GET` | `/api/v1/tenants/{tenant_id}/incident-drilldown?window_days=90&format=json` | `x-api-key` + `x-tenant-id`; Pfad **muss** zu `x-tenant-id` passen |
| `GET` | `/api/v1/advisors/{advisor_id}/tenants/{tenant_id}/incident-drilldown?…` | `x-api-key` + `x-advisor-id` (wie andere Advisor-Routen); Mandant muss in `advisor_tenants` verknüpft sein |

Query **`format`:** `json` (Standard) oder `csv` (UTF-8, Download-Header).

**Feature-Flag:** `governance_maturity` (wie Tenant-OAMI). Advisor-Zusatz: `advisor_workspace`.

## UI-Integration (Skizze)

- **Advisor Governance-Snapshot / Mandanten-Detail:** Abschnitt *„Incident-Drilldown (System / Lieferant)“* – Tabelle: `ai_system_name`, `supplier_label_de`, `incident_total_90d`, Spalten für Kategoriezähler oder ein einfaches Badge aus den gewichteten Anteilen; Tooltip mit `oami_local_hint_de`.
- **Intern:** CSV-Export-Link auf `format=csv` für Analyse in Excel/Sheets.

## Code

- Modelle: `app/incident_drilldown_models.py`
- Logik: `app/services/tenant_incident_drilldown.py`
- Endpunkte: `app/main.py`

*Version: 1.0 – ergänzend zu `governance-operational-ai-monitoring.md`.*
