# Wave 56 - Connector Candidate Scoring

## Ziel

Wave 56 ergänzt den SAP/ERP-Blueprint um eine **erklärbare Priorisierungslogik** für
Connector-Kandidaten je Mandant:

- Welche Connector-Typen sind kurzfristig umsetzbar?
- Wo ist strategischer und Compliance-seitiger Nutzen am höchsten?
- Wo sind Blocker aktuell zu hoch (`not_now`)?

Kein ML-Scoring, keine Blackbox: regelbasiert, nachvollziehbar, tunebare Gewichte.

## Scoring-Modell

Pro Kandidat (`tenant_id` + `connector_type`) werden folgende Felder geliefert:

- `readiness_score`
- `blocker_score`
- `strategic_value_score`
- `compliance_impact_score`
- `estimated_implementation_complexity`
- `complexity_band` (`low|medium|high`)
- `recommended_priority` (`high|medium|low|not_now`)
- `rationale_summary_de`
- `rationale_factors_de`
- `score_total`

## Faktoren und Gewichte

Gewichte sind explizit im Response enthalten (`scoring_weights`) und im Service zentral definiert:

- Readiness: `35`
- Blocker (inverse): `20`
- Strategischer Wert: `25`
- Compliance-Impact: `20`

Formel:

`score_total = readiness*0.35 + (100-blocker)*0.20 + strategic*0.25 + compliance*0.20`

## Datenquellen (Reuse statt Duplikation)

- Enterprise Onboarding Readiness
  - SSO-Status, Role-Mapping-Status, Integrationsreadiness, Onboarding-Blocker
- SAP Evidence Connector Blueprint (Wave 55)
  - Connector-Typ, Domains, Security-Prerequisites, Status, Owner, Blocker
- Enterprise Control Center
  - offene Signale als Proxy für Compliance-/Operativitätsdruck
- Evidence-Hook-Nähe
  - über strukturierte `evidence_domains` und `evidence_ref`-nahe Mapping-Indikatoren

## API

- `GET /api/internal/enterprise/connector-candidates`
  - liefert `candidate_rows`, `top_priorities`, `grouped_priorities_by_connector_type`
  - optional Advisor-/Sales-Summary via `include_markdown=true`

## Rationale-Regeln (Beispiele)

- `high`: hoher Gesamtscore und niedrige Blocker-Belastung
- `medium`: guter Score, aber noch moderate Voraussetzungen offen
- `low`: begrenzter kurzfristiger ROI oder höhere Umsetzungslast
- `not_now`: zu viele Blocker oder zu schwache Readiness

## Nutzung durch GTM / Integration

- Advisor & Solutioning:
  - Erst-Connector für Workshop-/Discovery-Phase festlegen
- Enterprise Sales:
  - Upgrade- und Implementierungsreife pro Mandant transparent argumentieren
- Delivery:
  - Build-Reihenfolge nach erklärbarer Priorität planen

## Limitierungen

- Single-tenant Bewertung pro API-Call; kein Cross-Tenant-Ranking in dieser Welle
- Kein Umsatz-/Vertragsdatenzugriff
- Keine live-technische Konnektivitätsprüfung (nur Readiness-/Blueprint-Metadaten)

## Security und Auditierbarkeit

- Tenant-scharf und RBAC-geschützt (`view_dashboard`)
- Keine Speicherung von Credentials/Secrets
- Begründungen basieren auf strukturierten, prüfbaren Feldern
