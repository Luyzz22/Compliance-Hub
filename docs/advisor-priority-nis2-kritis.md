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

## Verwandte Dokumente

- [advisor-portfolio-prioritization.md](./advisor-portfolio-prioritization.md) – Basispriorität und Filter
- Code: `app/services/advisor_portfolio_priority.py`, `app/services/advisor_portfolio.py`
