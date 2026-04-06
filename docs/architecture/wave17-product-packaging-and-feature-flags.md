# Wave 17 — Product Packaging & Feature-Flag Model

## Overview

Wave 17 introduces ComplianceHub's internal product packaging model: tiers,
bundles, capabilities, and enforcement — so the platform can be sold in
coherent packages for DACH enterprise and Kanzlei customers.

**Key principle:** capabilities are enforced on the backend (not just hidden in
the UI). No billing integration in this wave — pure feature gating.

---

## 1. Tier / Bundle / Capability Model

### Product Tiers

| Tier | Target Segment | Default Bundles |
|---|---|---|
| **Starter** | KMU-Einstieg | AI Act Readiness |
| **Professional** | Kanzlei / wachsender Mittelstand | AI Act Readiness + AI Governance & Evidence |
| **Enterprise** | SAP-Mittelstand / Konzern | All bundles |

### Product Bundles

| Bundle | Capabilities Included |
|---|---|
| `ai_act_readiness` | `cap_ai_advisor_basic`, `cap_ai_evidence_basic` |
| `ai_governance_evidence` | `cap_ai_advisor_basic`, `cap_ai_evidence_basic`, `cap_grc_records`, `cap_ai_system_inventory`, `cap_kanzlei_reports` |
| `enterprise_integrations` | `cap_enterprise_integrations`, `cap_kanzlei_reports` |

### Capability Flags

| Capability | Description |
|---|---|
| `cap_ai_advisor_basic` | AI Act Advisor (RAG + presets) |
| `cap_ai_evidence_basic` | AI Act Evidence & Nachweise |
| `cap_grc_records` | GRC records (Risk, NIS2, ISO 42001) |
| `cap_ai_system_inventory` | AI system inventory & lifecycle |
| `cap_kanzlei_reports` | Mandanten-Board-Reports & Dossiers |
| `cap_enterprise_integrations` | Enterprise connectors (SAP/DATEV) |

### Resolution

```
Tenant → TenantPlanConfig (tier + optional extra bundles)
  → effective_bundles() = tier defaults ∪ explicit overrides
  → capabilities() = union of all bundle capabilities
  → has_capability(cap) = cap ∈ capabilities()
```

---

## 2. Example SKUs

### AI Act Readiness (Starter)

- Advisor basics (RAG, presets for AI Act risk assessment)
- Evidence views (AI Act documentation tracking)
- No GRC entities, no integrations, no board reports
- **Target:** KMU / SME starting their AI Act journey

### AI Governance Suite (Professional)

- Everything in Starter
- GRC records (AiRiskAssessment, NIS2, ISO 42001 gaps)
- AI system inventory with lifecycle & readiness
- Mandanten-Board-Reports & Kanzlei-Dossiers
- **Target:** Steuerberater/WP-Kanzleien, growing Mittelstand

### Enterprise Connectors (Enterprise add-on)

- Everything in Professional
- DATEV export artifacts & SAP BTP envelopes
- Integration job management (outbox, dispatcher, retry)
- SAP S/4 inbound endpoint
- **Target:** SAP-centric enterprises, large Kanzleien with system integrations

---

## 3. API Enforcement

Capability checks are enforced **on the backend** at the endpoint level,
after OPA role checks:

```python
require_capability(auth.tenant_id, Capability.grc_records)
```

### Protected Endpoints

| Endpoint Group | Required Capability |
|---|---|
| GRC APIs (`/api/v1/grc/*`) | `cap_grc_records` |
| AI System Inventory (`/api/v1/ai-systems`) | `cap_ai_system_inventory` |
| Client Board Reports | `cap_kanzlei_reports` |
| Mandant-Dossier Export | `cap_kanzlei_reports` |
| Integration Jobs | `cap_enterprise_integrations` |
| SAP Inbound Endpoint | `cap_enterprise_integrations` |

### Error Response

When a capability is missing, the API returns HTTP 403 with a standardized
bilingual error:

```json
{
  "error": "feature_not_enabled",
  "message_en": "This feature (GRC Records) is not included in your current plan. Contact your ComplianceHub representative to upgrade.",
  "message_de": "Diese Funktion (GRC-Einträge) ist in Ihrem aktuellen Paket nicht enthalten. Kontaktieren Sie Ihren ComplianceHub-Ansprechpartner für ein Upgrade.",
  "capability": "cap_grc_records"
}
```

---

## 4. UI Integration

The workspace meta endpoint (`/api/v1/workspace/tenant-meta`) now includes:

```json
{
  "plan_tier": "pro",
  "plan_display": "Professional – AI Act Readiness, AI Governance & Evidence",
  "plan_capabilities": [
    "cap_ai_advisor_basic",
    "cap_ai_evidence_basic",
    "cap_ai_system_inventory",
    "cap_grc_records",
    "cap_kanzlei_reports"
  ]
}
```

The frontend can use `plan_capabilities` to:
- Show/hide navigation items
- Enable/disable workflow buttons
- Display "In Ihrem aktuellen Paket nicht enthalten" tooltips

---

## 5. Demo Tenant Profiles

Pre-configured profiles for sales demos:

| Profile | Tier | Use Case |
|---|---|---|
| `kanzlei_demo` | Professional | Kanzlei with governance + evidence |
| `sap_demo` | Enterprise | Full platform including integrations |
| `sme_demo` | Starter | SME with AI Act Readiness only |

Apply via:
```
POST /api/internal/product/demo-seed/{tenant_id}?profile=kanzlei_demo
```

---

## 6. Usage Metrics

Feature usage is tracked per tenant and capability:

```json
{
  "event_type": "capability_usage",
  "tenant_id": "kanzlei-mueller",
  "capability": "cap_grc_records",
  "action": "list_risks",
  "tier": "pro",
  "bundle": "ai_governance_evidence"
}
```

No PII — only aggregated counts per tenant/capability/bundle for future
pricing decisions.

---

## 7. Admin APIs

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/internal/product/plan` | GET | Get current tenant's plan |
| `/api/internal/product/plan/{tenant_id}` | PUT | Set a tenant's plan |
| `/api/internal/product/demo-seed/{tenant_id}` | POST | Apply demo profile |

---

## 8. Files

| File | Purpose |
|---|---|
| `app/product/__init__.py` | Package marker |
| `app/product/models.py` | Tier, Bundle, Capability enums + TenantPlanConfig |
| `app/product/plan_store.py` | In-memory store, has_capability, require_capability, metrics |
| `app/product/demo_plans.py` | Pre-configured demo profiles |
| `app/demo_models.py` | Extended TenantWorkspaceMetaResponse with plan fields |
| `app/main.py` | Capability enforcement on endpoints + plan APIs |
| `tests/test_product_packaging.py` | 31 tests |

---

## 9. Design Decisions

- **In-memory store:** Plan configs are stored in-memory (like GRC/integration stores).
  Future: migrate to DB alongside tenant registry.
- **Default = Starter:** Tenants without explicit plan config get the Starter tier.
  This is safe: new tenants start with basic capabilities.
- **Additive bundles:** A Starter tenant can have `enterprise_integrations` added
  without upgrading to Enterprise tier. This supports flexible commercial packaging.
- **No billing integration:** This wave is purely internal feature gating.
  Stripe/billing integration is a separate concern.
- **Bilingual errors:** All capability-denied messages include German + English
  text, fitting the DACH market focus.
