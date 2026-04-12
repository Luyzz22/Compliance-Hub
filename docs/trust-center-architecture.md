# Trust Center & Assurance Portal – Architecture

## Overview

The Customer Trust Center & Assurance Portal provides a structured, controlled,
and self-service-capable layer for ComplianceHub's compliance evidence,
security information, and assurance artefacts. It serves prospects, customers,
auditors, and internal reviewers with role-based access to trust-related content.

## Content Classification

| Layer | Visibility | Example Content |
|-------|-----------|-----------------|
| **Public Trust Center** | Unauthenticated | Security overview, compliance overview, frameworks, data residency, subprocessor transparency, contact / security review request |
| **Gated Assurance Portal** | Authenticated + role-gated | Policies, certificates, audit reports, TOMs, compliance snapshots, board/assurance PDFs |
| **Evidence Bundles** | Authenticated + `ACCESS_EVIDENCE_BUNDLES` | Pre-assembled due-diligence packages (ISO 27001, NIS2, DSGVO, EU AI Act, GoBD) |

## Roles & Access Levels

The Trust Center reuses the existing `EnterpriseRole` hierarchy and extends it
with four new permissions:

| Permission | Description | Minimum Role |
|-----------|-------------|-------------|
| `VIEW_TRUST_CENTER` | View gated assurance portal content | VIEWER |
| `MANAGE_TRUST_CENTER` | Manage / publish trust center assets | COMPLIANCE_ADMIN |
| `ACCESS_EVIDENCE_BUNDLES` | Generate & download evidence bundles | AUDITOR |
| `DOWNLOAD_ASSURANCE_DOCS` | Download individual gated documents | CONTRIBUTOR |

Portal access tiers map as follows:

| Tier | EnterpriseRole(s) |
|------|------------------|
| public visitor | (none – unauthenticated) |
| prospect | VIEWER |
| customer | CONTRIBUTOR, EDITOR |
| auditor | AUDITOR |
| internal reviewer | COMPLIANCE_OFFICER, COMPLIANCE_ADMIN, CISO, TENANT_ADMIN |

## Asset / Document Classification

Each trust center asset carries:

- `asset_type`: policy, certificate, audit_report, tom, compliance_snapshot, board_pdf
- `sensitivity`: public, prospect, customer, auditor, internal
- `framework_refs`: list of applicable frameworks (e.g. ISO_27001, NIS2, DSGVO)
- `valid_from` / `valid_until`: temporal validity
- `review_date`: last review timestamp
- `published`: boolean – only published assets are visible

## Evidence Bundle Types

| Bundle Key | Content | Target Audience |
|-----------|---------|-----------------|
| `iso_27001` | ISMS policies, control mappings, audit log exports, risk summaries | ISO auditors |
| `nis2` | NIS2 obligation mapping, incident summaries, control evidence | NIS2 assessors |
| `dsgvo` | DSGVO/GDPR processing records, TOM documentation, DPA evidence | DPOs, regulators |
| `eu_ai_act` | AI register, risk classifications, human oversight evidence | AI Act supervisors |
| `gobd_revision` | GoBD compliance evidence, DATEV exports, audit trails | Tax auditors |
| `vendor_security_review` | Security overview, architecture, control summary | Procurement teams |
| `auditor_bundle` | Full audit evidence package across all frameworks | External auditors |

## Compliance Mapping View

Visualises "map once, comply many":

- Rows: Controls / evidence artefacts
- Columns: Frameworks (EU AI Act, ISO 42001, ISO 27001, NIS2, DSGVO, GoBD)
- Cells: Coverage level (full, partial, planned, not_applicable)
- High-level view for business / procurement
- Detail view for auditors / security reviewers

## Access Audit

All access to gated content and evidence bundles is logged:

- `trust_center_access_logs` table captures: who, what, when, action, IP
- Downloads trigger immutable audit log entries
- Bundle generation events are traceable

## Review & Approval Logic

- Assets have a `published` flag controlled by `MANAGE_TRUST_CENTER` roles
- Evidence bundles are assembled from existing tenant artefacts (no separate document store)
- Bundle metadata includes: created_at, validity_date, tenant/scope, sensitivity level

## Technical Integration

- Reuses existing RBAC (`app/rbac/`) and tenant isolation (`x-tenant-id`)
- No separate auth or rights system
- Backend: FastAPI endpoints under `/api/v1/trust-center/`
- Frontend: Next.js pages at `/trust-center` (public) and `/tenant/trust-center` (gated)
- All DB models in `app/models_db.py`, migration in `app/db_migrations/`
