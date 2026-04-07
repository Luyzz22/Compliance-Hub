# Wave 55 - SAP Evidence Connector Blueprint

## Zielbild

Wave 55 liefert eine **metadata-first Integrations-Blueprint- und Playbook-Schicht** fuer DACH-Enterprise-
Mandanten. Die Welle bereitet SAP BTP / S/4HANA / DATEV / Dynamics Anbindungen fuer Nachweisdaten vor,
implementiert aber bewusst **keine Live-Connectoren und keine Credential-Verwaltung**.

## Blueprint-Modell

Jeder Blueprint-Eintrag bildet einen priorisierbaren Integrationskandidaten je Tenant ab:

- `blueprint_id`
- `tenant_id`
- `source_system_type` (`sap_btp`, `sap_s4hana`, `datev`, `ms_dynamics`, `generic_api`)
- `evidence_domains` (z. B. `invoice`, `approval`, `access`, `vendor`, `ai_inventory`, `policy_artifact`)
- `onboarding_readiness_ref`
- `security_prerequisites`
- `data_owner`, `technical_owner`
- `integration_status` (`planned`, `designing`, `blocked`, `ready_for_build`)
- `blockers`, `notes`

Persistenz erfolgt tenant-scharf in `enterprise_integration_blueprints`.

## Evidence-Domain-Mapping (Blueprint-Ebene)

- **SAP S/4HANA**: `invoice`, `approval`, `vendor`, `workflow_evidence`, `access`
- **SAP BTP**: `workflow_evidence`, `access`, `policy_artifact`
- **DATEV**: `invoice`, `tax_export_context`
- **Microsoft Dynamics**: `invoice`, `approval`, `access`, `vendor`
- **Generic API**: `ai_inventory`, `policy_artifact`

Das Mapping wird mit der bestehenden Onboarding-Readiness und Evidence-Hook-Logik ausgerichtet, statt
parallel eine neue Nachweis-Logik zu schaffen.

## Interne API

- `GET /api/internal/enterprise/integration-blueprints`
  - liefert Blueprint-Zeilen, aggregierte Readiness, Blocker, Top-Kandidaten
  - optional `markdown_de` Playbook-Zusammenfassung via `include_markdown=true`
- `PUT /api/internal/enterprise/integration-blueprints`
  - upsert einzelner Blueprint-Zeilen
  - RBAC-geschuetzt (`manage_onboarding_readiness`)
  - GoBD-konform audit-logged

## Playbook-Artefakt

Die API erzeugt optional ein wiederverwendbares deutsches Markdown-Artefakt mit:

- empfohlenem ersten Connector
- erforderlichen Voraussetzungen
- freigeschalteten Evidence-Domaenen
- Risiko-/Blocker-Sicht
- naechsten Umsetzungsstufen fuer Connector-Build-Waves

Damit wird eine klare Bruecke zwischen interner Solutioning-Planung, Partner-Alignment und
Kunden-Workshops geschaffen.

## Reuse in Enterprise-Artefakten

- **Onboarding Readiness Cockpit**: Integration-Posture + Top-Kandidaten eingeblendet
- **Enterprise Control Center**: kompaktes Panel "Integration Blueprint"
- **Authority & Audit Preparation Pack**: Section G mit Integrations-Posture
- **Board/Management**: nur indirekter Bezug ueber posture-relevante Readiness-Signale

## Security und Auditierbarkeit

- Tenant-Grenzen bleiben strikt (`tenant_id` Pflicht auf allen Abfragen/Updates)
- Blueprint-Aenderungen sind RBAC-geschuetzt
- Aenderungen werden ueber Governance-Audit-Taxonomie protokolliert
- Es werden keine Secrets, Tokens oder Live-Zugangsdaten gespeichert

## Weiterer Pfad zu Live-Connectoren

1. Schnittstellenvertraege je Quellsystem finalisieren (Objekte, Feldmapping, Delta-Strategie)
2. BTP-/API-Adapter fuer priorisierten Kandidaten in separater Build-Wave implementieren
3. Evidence-Ingestion mit Audit-Trail, Retry-Strategie und Tenant-Isolation produktivieren
4. Connector-Health, SLA und Incident-Rueckkopplung in Control Center erweitern
