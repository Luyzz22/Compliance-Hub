# Wave 54 – Enterprise Onboarding Readiness

## Zielbild

Wave 54 liefert eine kompakte, auditable Onboarding-Readiness-Schicht fuer Enterprise-Rollout:

- Tenant-/Organisationsstruktur sichtbar und versionierbar
- SSO-Readiness modelliert (ohne Voll-IAM-Implementierung)
- Identity->Role-Mapping an bestehendes RBAC angebunden
- SAP-BTP-/Integrationspfade als readiness-orientierte Planungsobjekte

## Tenant model

Persistenz: `enterprise_onboarding_readiness` je Tenant.

Strukturfelder:

- `enterprise_name`
- `tenant_structure` (business units, subsidiaries, parent relationships)
- `advisor_visibility_enabled`

Bestehendes Advisor-Mandantenmodell bleibt unverändert; Wave 54 ergänzt nur Readiness-Metadaten.

## SSO readiness model

- `provider_type`: `azure_ad`, `saml_generic`, `sap_ias`, `google_workspace`, `okta`, `other`
- `onboarding_status`: `not_started`, `planned`, `configured`, `validated`
- `role_mapping_status`: gleiches Statusmodell
- `identity_domain`, `metadata_hint`
- `role_mapping_rules`: externe Gruppen/Claims -> ComplianceHub-Rollen

## Role mapping principles

- Reuse bestehende Rollen (`EnterpriseRole`) statt Enterprise-Sonderrollen.
- Safe mapping checks:
  - keine duplizierten Gruppen/Claim-Keys
  - begrenzte High-Privilege-Mappings (Least Privilege Leitlinie)
- Mapping-Validierung dient als Readiness-Hinweis, nicht als Vollersatz fuer IAM-Reviews.

## Integration readiness model

Integrationsziele:

- `sap_btp`, `sap_s4hana`, `datev`, `ms_dynamics`, `generic_api`

Status:

- `not_started`, `discovery`, `mapped`, `ready_for_implementation`

Pro Ziel:

- Owner, Notes, Blocker, Evidence reference

## APIs and security

- `GET /api/internal/enterprise/onboarding-readiness`
  - tenant-safe baseline/read model
  - RBAC: `view_dashboard`
- `PUT /api/internal/enterprise/onboarding-readiness`
  - update model
  - RBAC: `manage_onboarding_readiness`
  - governance-audit logged (`enterprise_onboarding_readiness.upsert`)

## UI

Tenant panel:

- `/tenant/onboarding-readiness`
- Einstieg im Enterprise Control Center
- Fokus auf Blocker, SSO-Status, Tenant-Struktur und Integrationsziele

## Limitations / next steps

- Kein vollwertiges IAM-/SSO-Produkt in dieser Welle.
- Keine tiefen Connectoren; nur readiness-orientierte Integrationsplanung.
- Nächster Schritt: technische Connector-Implementierung und IdP-Handshake-Validierung pro Zielplattform.
