# AI & Compliance Readiness Score

Der **Readiness Score** (0–100) fasst Mandantensignale aus dem bestehenden ComplianceHub-Datenbestand zu einer verkaufs- und boardtauglichen Kennzahl zusammen. Er ersetzt keine Rechts- oder Auditbewertung; er dient Priorisierung, Demos und Berater-QBRs.

## Dimensionen und Gewichtung

| Dimension | Gewicht | Quelle (Backend) |
|-----------|---------|------------------|
| Setup & Wizard | 20 % | AI-Governance-Setup-Wizard (Schritte 1–6) bzw. bei ausgeschaltetem Wizard der Guided-Setup-Fortschritt |
| Framework-Coverage | 30 % | Mittlere Cross-Regulation-`coverage_percent` über aktivierte Frameworks (oder alle, falls keine Auswahl) |
| KPI-Readiness | 20 % | Anteil High-Risk-/Unacceptable-Systeme mit mindestens **2** erfassten KPI-Definitionen (Zeitreihen) |
| Gap-Last | 20 % | Anteil **kritischer** regulatorischer Gaps (`criticality == high`) an Gesamtpflichten im gleichen Framework-Scope, invertiert |
| Report-Reife | 10 % | Board-/Advisor-Reports: 0 → 0, 1 → 0,5, ≥ 2 → 1,0 (normalisiert) |

## Level-Labels

- **basic**: Score &lt; 45  
- **managed**: 45–69  
- **embedded**: ≥ 70  

## Regulatorischer Bezug

- **EU AI Act**, **ISO 42001**, **ISO 27001**, **NIS2**, **DSGVO** (ISO 27701) fließen über die **aktivierten Frameworks** im Setup-Wizard und die Cross-Regulation-Abdeckung ein; der Score spiegelt **Ist-Coverage und Lücken** im Tool, keine Zertifizierung.

## API

- Mandant: `GET /api/v1/tenants/{tenant_id}/readiness-score` (Tenant-Header muss passen)  
- Optional KI-Erklärung: `POST /api/v1/tenants/{tenant_id}/readiness-score/explain` (benötigt `COMPLIANCEHUB_FEATURE_LLM_ENABLED` und `COMPLIANCEHUB_FEATURE_LLM_EXPLAIN`). Prompt über `app/services/readiness_explain_prompt.build_readiness_explain_prompt` (baut auf `governance_maturity_contract` auf, inkl. `GOVERNANCE_MATURITY_CONTRACT_VERSION`). Antwort: Fließtext `explanation` plus optional `readiness_explanation` / `operational_monitoring_explanation` (JSON-Enums wie Score-API; UI-Labels im Frontend aus `governanceMaturityDeCopy`). Vertrag: `docs/governance-maturity-copy-contract.md`.  
- Berater-Proxy: `GET /api/v1/advisors/{advisor_id}/tenants/{tenant_id}/readiness-score` (nur verknüpfte Mandanten)  

Feature-Flag: `COMPLIANCEHUB_FEATURE_READINESS_SCORE` / `NEXT_PUBLIC_FEATURE_READINESS_SCORE`.

## Sales-Stichwort

„Ein Score, der Setup, Normen-Coverage, KPI-Monitoring, regulatorische Gaps und Board-Reports bündelt – ideal für Pilot-Check-ins und Executive One-Pager.“
