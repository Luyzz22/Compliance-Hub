# Enterprise Transformation Operating Model

Status: active governance baseline
Executive sponsor: repository owner / future managing director
Review cadence: weekly delivery review, monthly risk committee, quarterly board gate

## Objective

Build Compliance Hub into an evidence-backed enterprise AI governance platform without allowing
commercial urgency to override security, privacy, legal, model-risk, or operational-resilience
requirements. Claims are released only when the underlying control and its operating evidence exist.

## Decision bodies

| Body | Accountable decisions | Required participants |
|---|---|---|
| Board / executive sponsor | Risk appetite, funding, market claims, production launch, accepted residual risk | CEO/MD, product, security, privacy/legal |
| AI governance committee | Model/provider approval, use-case classification, human oversight, evaluation thresholds | AI lead, product, legal, DPO, domain owner |
| Architecture review board | Identity, tenant isolation, data boundaries, platform standards, irreversible technical choices | CTO/IT lead, security architect, platform lead, data/AI lead |
| Change advisory group | Production change window, rollback, migration and operational readiness | Platform, SRE/operations, security, product owner |
| Incident command | Containment, notification assessment, customer/regulator communications | Incident commander, CISO, DPO/legal, service owner |

No individual may approve their own high-risk exception. Security, privacy and AI-governance owners
have stop-the-line authority for production releases.

## Three lines of accountability

1. Product and engineering own correct implementation and daily control operation.
2. Security, privacy, legal and AI governance define policy, challenge evidence and monitor risk.
3. Independent assurance validates design and operating effectiveness before material release claims.

## Stage gates

| Gate | Decision | Minimum evidence |
|---|---|---|
| G0 — Problem | Should this capability exist? | User need, regulatory role, data classification, accountable owner |
| G1 — Architecture | Is the design safe to build? | ADR, threat model, privacy assessment, misuse cases, tenant boundary |
| G2 — Implementation | Is the control implemented? | Reviewed code, tests, dependency/SAST results, migration and rollback |
| G3 — Pre-production | Is it operable? | Production-like test, runbooks, monitoring, alerts, backup/restore, access review |
| G4 — Production | May it launch? | Named approvals, immutable evidence pack, zero open critical/high findings |
| G5 — Continuous assurance | May it remain live? | SLOs, incidents, drift, access recertification, model/provider and control reviews |

## Board scorecard

The scorecard is based on evidence, not self-attestation:

- zero unresolved critical/high security findings at release;
- 100% protected routes with server-side authentication and tenant authorization tests;
- 100% model calls linked to tenant policy, provider, model/deployment, purpose and review state;
- zero prompts/responses in logs unless a separately approved data-retention design exists;
- 100% subprocessors and Azure resources mapped to an owner, region and contract record;
- recovery objectives demonstrated by restore tests, not configuration screenshots;
- access reviews, secrets rotation and incident exercises completed within approved cadence;
- customer-facing compliance claims mapped to current evidence and expiry dates.

## Current board decision

Production remains blocked. The highest-risk dependency is the identity and tenant boundary. The
active delivery sequence is:

1. implement server-side sessions and tenant-bound roles;
2. introduce a same-origin Next.js BFF and remove browser bearer keys;
3. enforce authorization again in every server route and backend operation;
4. activate the implemented Microsoft Entra ID OIDC boundary only after MFA/Conditional Access,
   provisioning, credential and access-review evidence; password authentication is disabled by
   production policy when Entra is active;
5. migrate local JSON stores and simulated integrations to governed platform services;
6. complete legal, privacy, Azure landing-zone and independent-assurance evidence.

## Delivery decision record — identity wave 2

The architecture and implementation gates for the new browser identity substrate are evidenced, but
the production gate remains closed. The board accepts the following sequence without accepting the
residual risks for production:

1. merge the revocable tenant session and BFF foundation after CI-equivalent verification;
2. configure and independently approve the implemented Entra ID flow, app roles, MFA/Conditional
   Access, provisioning lifecycle and credential strategy;
3. migrate every legacy Route Handler and Server Component from service keys/local identity hints;
4. replace local JSON/file persistence with governed Azure data services and backup/restore evidence;
5. complete Azure regional, DPA/subprocessor, DPIA, retention and independent penetration-test gates.

No environment may set `COMPLIANCEHUB_ENTERPRISE_AUTH_READY=true` until steps 2 and 3 have named
security approval and negative cross-tenant evidence for every protected route family.
