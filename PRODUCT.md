# Compliance Hub

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary users are DACH compliance, information-security and AI-governance leaders who need to understand and control AI-related obligations across systems, controls, evidence and accountable owners. Board members, auditors, advisors and procurement stakeholders evaluate the same information at different levels of detail. The repository also supports multi-client advisory work for tax, audit and GRC firms.

## Product Purpose

Compliance Hub is an enterprise governance workspace for connecting AI-system inventories, regulatory obligations, controls, evidence, reviews and board decisions. Success means that teams can see unresolved governance work, assign accountability and prepare reviewable evidence without treating software output as legal advice or automatic approval.

## Positioning

The product joins multiple regulatory frameworks to a tenant-scoped control and evidence model. Human review, explicit ownership, audit history and fail-closed release gates remain part of the mechanism instead of being added as marketing assurances.

## Operating Context

The product is evaluated by regulated DACH organizations and advisory firms. It is designed to sit alongside identity providers, DMS, GRC, ticketing, SIEM and Azure services. The public website is a stateless product-information release; authenticated enterprise data, APIs and AI functions are released separately only after the documented evidence gates are satisfied.

## Capabilities and Constraints

- Multi-tenant AI-system inventory, risk classification and cross-regulation control mapping.
- Evidence, remediation, audit, incident and board-reporting workflows with role-based access.
- Article 50 and GDPR transparency-assurance records with owner, reviewer, evidence and review dates.
- Versioned DSFA/DPIA and FRIA impact-assessment records with separate scope decisions, eight evidence-proximate review fields, four-eyes approval and consultation gates.
- Azure OpenAI support with Managed Identity as the production standard, PII and prompt-injection blocking, and feature flags disabled until regional and operational evidence is approved.
- The platform supports governance and documentation. It does not certify legal conformity, replace qualified review or make binding legal and approval decisions.
- Public routes, enterprise routes and release profiles must remain technically separated.

## Brand Commitments

The product name is Compliance Hub. The public language is German and uses the established terms Governance, Controls, Evidence, Human Review, Trust Center and Board Readiness. The voice is precise, restrained, technically credible and explicit about limits. Existing route names, legal disclosures, contact flows and the three governance hero assets must be preserved.

## Evidence on Hand

- Product implementation and tests in `app/`, `frontend/src/app/`, `frontend/src/components/` and `tests/`.
- Security, architecture and release evidence in `docs/`, especially `docs/enterprise-readiness-20260714.md`, `docs/enterprise/wave60-article50-transparency-assurance.md` and `docs/enterprise/wave61-dpia-fria-impact-assessment.md`.
- Public trust disclosures in `frontend/src/app/trust-center/page.tsx`.
- Three owned high-resolution governance visuals in `frontend/public/images/hero/`.
- No approved public customer logos, testimonials, certifications or production performance benchmarks are available and none may be fabricated.

## Product Principles

1. Evidence before assertion.
2. Human accountability remains visible.
3. Tenant and release boundaries fail closed.
4. Complex regulation is translated into reviewable operational work.
5. Public communication distinguishes implemented controls from pending operational approval.

## Accessibility & Inclusion

Public and product surfaces target WCAG 2.2 AA, preserve keyboard operation and visible focus, support reduced motion and use plain German explanations alongside specialist terminology.
