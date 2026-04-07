# Enterprise Hardening & Simplification Wave (2026-04-07)

This wave is a focused hardening/refactoring pass based on the Copilot deep-repo analysis PR.
It introduces no new product-surface capabilities. It improves security consistency, architectural
clarity, and maintainability for upcoming Phase-3+ work (RAG gap engine, DATEV, advanced board packs).

## 1) Prioritized findings (Copilot analysis)

Top issues for DACH enterprise customers:

1. Security-critical audit action/entity strings were scattered across endpoints, raising drift risk.
2. NIS2 deadline defaults (`24h/72h/+30d`) were embedded in repository logic without central policy constants.
3. `app/main.py` remains monolithic, making boundary enforcement and review harder.
4. Governance concepts (incidents, deadlines, calendar, audit events) were partially duplicated in docs/code.
5. RLS enforcement is repository-convention based; production-level DB guarantees still need completion.
6. API security hardening backlog remains (rate limiting / anti-abuse protections).
7. Runtime/auth posture still leans on API-key workflows; broader enterprise SSO/JWT rollout remains pending.

## 2) Scope decisions for this wave

### In scope (implemented now)

- Central shared governance taxonomy for audit entities/actions:
  - `app/governance_taxonomy.py`
- Central NIS2 deadline policy constants in same taxonomy module.
- Endpoint refactor to consume canonical taxonomy values:
  - NIS2 mutation audit events
  - Compliance calendar mutation audit events
  - Authority export audit event
- Repository refactor to consume canonical NIS2 deadline offsets.
- Regression tests for taxonomy stability and NIS2 policy defaults.

### Deferred backlog (explicitly not in this wave)

- Split `app/main.py` into domain routers.
- Enforce append-only / tenant guardrails with DB-native triggers + RLS for every enterprise table.
- Rate limiting and abuse controls for enterprise endpoints.
- Full SSO/JWT migration and API-key posture reduction.
- Cross-layer canonical aggregate builders for all advisor/enterprise reporting views.

### Out of scope for this wave

- New feature development (DATEV export, SAP integration, new board surfaces).
- Large-scale performance rewrites.
- UI redesigns.

## 3) Mapping: Copilot finding -> status

| Copilot finding | Status | Handling |
| --- | --- | --- |
| Scattered security/event literals | Fixed | Introduced `governance_taxonomy.py`; wired key endpoints/repository to typed constants |
| NIS2 deadline policy implicit in logic | Fixed | Centralized in `NIS2DeadlinePolicy` |
| Monolithic `app/main.py` | Deferred | Tracked as next hardening wave (router extraction) |
| Inconsistent concept boundaries | Partially fixed | Taxonomy and docs unified for incidents/calendar/audit semantics |
| RLS completeness in production | Deferred | Keep as infra hardening backlog item |
| Rate limiting / DDoS posture | Deferred | Security backlog (gateway/platform) |
| API-key-centric auth posture | Deferred | Enterprise auth roadmap item |

## 4) Updated architecture notes

### Permissions

- RBAC remains canonical via `app/rbac/permissions.py` + `require_permission(...)`.
- This wave keeps permission model intact and reduces drift in downstream audit semantics.

### Audit/events

- Canonical names now live in `app/governance_taxonomy.py`.
- Security-sensitive governance endpoints use taxonomy values, reducing accidental action/entity divergence.

### Incident/calendar/reminder/SLA boundaries

- NIS2 workflow remains the canonical incident engine.
- Compliance calendar remains canonical for obligation deadlines.
- This wave centralizes only incident/calendar audit semantics and deadline defaults; reminder/SLA convergence
  remains a follow-up refactor to keep this PR tight.

### Advisor vs enterprise layers

- Enterprise governance logic continues to extend existing advisor stack.
- This wave improves shared semantics without introducing a forked reporting path.
