# ComplianceHub Roadmap

**Last Updated:** 2026-04-06

---

## ✅ Completed — Enterprise Sprint (2026-04-06)

### Priority 1: Security & Compliance
- [x] **GoBD §14 Audit Log Service** — SHA-256 hash chaining, GoBD XML export,
      IP/user-agent tracking, chain integrity verification
- [x] **Enterprise RBAC + ABAC** — 9 roles (VIEWER → SUPER_ADMIN), 18 permissions,
      OPA policy integration, `require_permission()` FastAPI dependency
- [x] **NIS2 Incident Response Workflow** — ENISA taxonomy, 5 workflow states,
      24h/72h BSI deadline auto-calculation, strict transition enforcement
- [x] **Compliance Calendar + Deadline Management** — DACH regulatory deadlines,
      escalation engine (30/14/7 day alerts), iCal export

---

## 🔜 Next Sprint — Priority 2: Market Differentiation

### Q2 2026
- [ ] **EU AI Act Compliance Wizard** — Art. 51 KI-Register, risk classification engine,
      conformity declaration generator (Art. 47)
- [ ] **DATEV ASCII Export** — SKR03/SKR04, EXTF Version 700, Buchungsstapel for
      Steuerberater integration
- [ ] **Board-Level PDF Reports** — PDF/A-3 archival, quarterly compliance report,
      auto-generation via workflow

### Q3 2026
- [ ] **SAP BTP Integration Layer** — RFC/BAPI adapter, OData V4 client,
      SAP IAS SSO (SAML 2.0), JIT user provisioning
- [ ] **RAG-powered Gap Analysis Engine** — pgvector embeddings, LangGraph agent,
      cross-regulation mapping, LangSmith observability
- [ ] **Multi-Tenant Onboarding Automation** — Self-service provisioning,
      SSO wizard, data import, Stripe feature-gating

---

## 📋 Backlog — Priority 3: Infrastructure & Scale

- [ ] Supabase RLS enforcement for all tables (production hardening)
- [ ] Rate limiting and DDoS protection (API-level)
- [ ] SAML 2.0 / Azure AD SSO integration
- [ ] Webhook system for SIEM integration (Splunk, QRadar)
- [ ] Multi-language support (DE/EN/FR for DACH+)
- [ ] E-Rechnung EN-16931 / XRechnung 3.0
- [ ] Docker/Kubernetes deployment configurations
- [ ] Playwright E2E tests for critical frontend flows
- [ ] Locust performance tests (>500 concurrent users)

---

## Key Milestones

| Date | Milestone | Status |
|------|-----------|--------|
| 2026-04-06 | Enterprise Security Sprint Complete | ✅ |
| 2026-06-30 | EU AI Act Wizard + DATEV Export | 🔜 |
| 2026-08-02 | **EU AI Act Full Applicability** | ⏳ |
| 2026-09-30 | SAP Integration + RAG Engine | 📋 |
| 2026-12-31 | Full Enterprise Feature Set | 📋 |
