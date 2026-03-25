# Board-What-if-Simulator

Der **What-if-Simulator** auf `/board/kpis` erlaubt CISO, Advisory oder Vorstand, **hypothetische Verbesserungen** von NIS2-/KRITIS-KPI-Zielwerten (und optional einen simulierten EU-AI-Act-Kontrollgrad je System) zu setzen, **ohne** produktive Daten zu ändern.

## Feature-Flags

- Backend: `COMPLIANCEHUB_FEATURE_WHAT_IF_SIMULATOR`
- Frontend: `NEXT_PUBLIC_FEATURE_WHAT_IF_SIMULATOR`

## API

`POST /api/v1/ai-governance/what-if/board-impact` mit Body:

```json
{
  "kpi_adjustments": [
    {
      "ai_system_id": "<id>",
      "kpi_type": "INCIDENT_RESPONSE_MATURITY",
      "target_value_percent": 90
    }
  ]
}
```

Unterstützte `kpi_type`-Werte: `INCIDENT_RESPONSE_MATURITY`, `SUPPLIER_RISK_COVERAGE`, `OT_IT_SEGREGATION`, `EU_AI_ACT_CONTROL_FULFILLMENT` (letzterer wirkt als Readiness-Zusatzmodell auf Basis des System-Compliance-Scores im Dashboard, nicht als DB-Feld).

## Logik (Kurz)

- Ausgangspunkt sind die **aktuellen** Board-KPIs, das Compliance-Overview und die Alert-Engine.
- KPI-Werte der NIS2-/KRITIS-Tabelle werden **in-memory** überschrieben; es gibt **keine** Persistenz.
- Die Antwort enthält u. a. Original vs. simulierte Readiness, NIS2-KPI-Mittel im Board-Objekt, Alert-Anzahlen sowie Listen neu entstandener bzw. entfallener Alerts (Signatur `kpi_key|severity`).

## UI

Bis zu **drei High-Risk-Systeme** auswählen, Zielwerte eintragen, „Simulation berechnen“. Verlinkung zu Maßnahmen/Action-Drafts für operative Nachverfolgung.
