# Phase 3: AI System Inventory and KI-Register

## Zielbild

Phase 3 operationalisiert EU AI Act Wizard, KI-Register und Behoerdenexport als zusammenhaengende, auditierbare Betriebsschicht je Mandant.  
Die Loesung ist bewusst deterministisch und advisor-safe: keine automatische Rechtsberatung, keine direkten RAG-Texte in Exporten.

## Kanonisches Modell

`ai_systems` bleibt das primäre Inventarobjekt. Darauf aufbauend:

- `ai_system_inventory_profiles` (1:1 je Mandant + AI-System)
  - Anbieterinformationen (`provider_name`, `provider_type`)
  - Use Case / Business Process
  - Scope-Flags: EU AI Act, ISO 42001, NIS2, DSGVO special risk
  - Registerstatus + Register-Metadaten
  - Authority-Reporting-Flags
- `ai_register_entries` (versionierte Historie je Mandant + AI-System)
  - `version` monoton steigend
  - Status (`planned`, `partial`, `registered`, `not_required`)
  - nationale Registerfelder / Authority-Referenzen
  - Flagging fuer meldepflichtige Incidents/Changes

Damit werden Wizard-Sessiondaten nicht als Registerdaten missbraucht.

## Entscheidungslogik Wizard

- Versionierte, testbare Logik in `app/services/eu_ai_act_wizard_decision.py`
  - `decision_version = eu_ai_act_v1`
  - nutzt bestehende Klassifikationslogik
  - liefert strukturierte Ableitungen fuer Inventory-Scope
  - kennzeichnet Ergebnis explizit als vorlaeufige Governance-Einschaetzung

## Authority Export

Endpoint: `GET /api/v1/authority/ai-act/export`

- Deterministische Datenbasis:
  - `ai_systems`
  - `ai_system_inventory_profiles`
  - letzte Version aus `ai_register_entries`
- Scopes:
  - `initial`
  - `updates`
  - `incident_context`
- Ausgabe:
  - strukturiertes JSON (`export`)
  - `markdown_de` Management-/Advisor-Zusammenfassung
- Guardrail:
  - keine Roh-RAG-Ausgaben im Export

## Security / Audit

- Tenant-bound APIs mit vorhandenem Auth-Context
- RBAC:
  - `view_ai_systems`, `edit_ai_systems`
  - `view_risk_register`, `edit_risk_register`
  - `export_audit_log` fuer Authority Export
- Audit:
  - Inventory/KI-Register Updates als `audit_events`
  - Authority Exporte in `audit_events` und `audit_logs` (GoBD-Kette)

## Advisor und Board Integration

- Advisor Snapshot enthaelt KI-Register-Posture:
  - registered / planned / partial / unknown
  - `advisor_attention_items` fuer priorisierte Nacharbeit
- Board Markdown enthaelt KI-Register-Posture in Executive Summary und KPI-Tabelle.

## Limitationen

- Kein vollautomatischer Legal-Engine-Ansatz
- Keine automatisierte Uebermittlung an externe Register in dieser Phase
- Scope-/Risk-Einschaetzungen bleiben validierungspflichtig durch Fachberatung
