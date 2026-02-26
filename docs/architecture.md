# Architecture Blueprint (Enterprise SaaS)

## 1. Product Topology

1. **Document Intake Layer**
   - Input: XRechnung, ZUGFeRD, Contract PDFs
   - Capability: Format detection, EN-16931 validation hooks, metadata extraction
2. **Compliance Orchestration Layer**
   - Rule & AI decisions (DSGVO/GoBD/E-Rechnung)
   - Human-in-the-loop approval queue
3. **Audit & Trust Layer**
   - Hash-based immutable event log
   - Timestamped evidence packages for audits
4. **Integration Layer**
   - DATEV export
   - ERP/CRM connectors (webhooks / n8n)

## 2. Reference Runtime (MVP)

- API: FastAPI
- Rule Engine: Python service module (`app/services/compliance_engine.py`)
- UI: Static dashboard for GTM demos
- Persistence: In-memory in MVP (production target: PostgreSQL + object store + WORM archive)

## 3. Enterprise Hardening Roadmap

- Multi-tenant RBAC + SCIM/SAML SSO
- Tenant-isolated encryption keys (BYOK option)
- Region-bound processing (Frankfurt first, sovereign expansion)
- Continuous controls monitoring for ISO 27001/SOC2 evidence
- SLA-aware retry workflows for malformed e-invoices

## 4. Enterprise Control Plane Additions

- Tenant Compliance Profile (region + policy flags)
- Platform Audit API for control-state export
- Severity-normalized action model for SOC/GRC integration
