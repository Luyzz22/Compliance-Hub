# Enterprise-Readiness Review — 14. Juli 2026

## Executive status

**Status: RED / production release blocked.**

This repository has received an initial enterprise hardening wave, but it is not yet possible to
make a truthful, evidence-backed claim that the product is fully GDPR, EU AI Act, NIS2, ISO 27001,
ISO 27701, or ISO 42001 compliant. Compliance is a property of the complete socio-technical system:
software, Azure configuration, contracts, subprocessors, people, procedures, records, risk
acceptance, and ongoing operation. Code alone cannot establish it.

The production release gate intentionally fails when legal, identity, tenant, hosting, privacy, or
Azure processing evidence is absent. No person should bypass the gate by setting an attestation
variable without an approved, dated evidence record.

## Evidence reviewed

- Repository `Luyzz22/Compliance-Hub`, default branch `main`, through commit `6f77506`, plus the
  current Entra identity hardening change set.
- Public deployment `https://complywithai.de/`, including public legal routes, selected protected
  product routes, HTTP response headers, SEO/security discovery routes, desktop rendering, and
  unauthenticated behavior.
- Backend authentication, identity, tenant/API-key boundary, LLM routing and guardrails.
- Frontend authentication flow, API access model, public pages, legal content and build controls.
- GitHub workflows, branch policy visibility, dependency manifests, tests and security tooling.

## Critical baseline findings

| Area | Baseline finding | Current disposition |
|---|---|---|
| Legal identity | Imprint, privacy notice and terms contained explicit placeholders | Replaced by structured operator data and a fail-closed legal release gate; real data and legal approval remain required |
| Authentication | Login returned identity data but created no durable session; protected UI routes were publicly reachable | Revocable tenant sessions, same-origin BFF and Entra OIDC code+PKCE are implemented. **Production remains blocked** pending Entra/Conditional Access/provisioning evidence, privileged step-up and complete route-family migration |
| Browser credentials | Multiple client modules referenced `NEXT_PUBLIC_API_KEY` and a shipped fallback key | Production scan now rejects public credential variables; legacy call sites remain an explicit blocker until migrated behind the authenticated BFF |
| Tenant isolation | Global API key could select an arbitrary tenant header | Global keys are disabled by default in production; tenant-specific key verification remains. Full user-to-tenant authorization evidence is still required |
| Password storage | Unsalted SHA-256 password digests | New passwords use Argon2id; successful legacy login rehashes automatically |
| Recovery tokens | Verification/reset tokens were stored in plaintext; registration exposed a verification token | Opaque tokens are hashed at rest; registration no longer returns verification secrets |
| LLM data protection | PII could pass when injection risk was not high | PII and prompt injection now block model calls by default; explicit non-production redaction mode exists |
| Azure GPT | No Azure OpenAI provider | Azure OpenAI v1 provider added with Managed Identity, HTTPS enforcement, EU processing attestation and sanitized errors |
| HTTP/browser security | Missing CSP and common browser headers; framework disclosure | Frontend/API security headers added, production API docs disabled, host/CORS allowlists introduced, framework header disabled |
| Discovery | `robots.txt`, sitemap and `security.txt` returned 404 | App Router metadata routes and a security contact route added |
| Supply chain | Frontend audit reported 12 vulnerabilities, including one critical | Dependencies updated and PostCSS overridden; local `npm audit` reports zero known vulnerabilities as of this review |
| CI | No frontend build/test/audit, SAST, dependency review, or scheduled analysis | CI expanded; pinned actions, frontend checks, pip/npm audits, Bandit, OPA, CodeQL, Dependabot and CODEOWNERS added |
| Repository governance | Default branch was not protected; no security policy; no license | Security policy and ownership added. Branch rules and license selection require repository-owner action |

## Controls implemented in this wave

### Identity and secrets

- Argon2id password hashing with parameters recorded in each encoded hash.
- Constant-time bearer credential comparisons.
- SHA-256 lookup digests for high-entropy one-time verification and reset tokens; legacy plaintext
  rows remain readable only for migration compatibility.
- No verification token in the public registration response.
- Global cross-tenant API keys disabled by default for production environments.
- Encrypted OIDC state/nonce/PKCE transaction, tenant-specific Entra ID token verification and
  immutable `tid` + `oid` identity binding.
- Entra application-role enforcement plus explicit local identity provisioning; local tenant role
  remains authoritative and e-mail claims never grant access.
- Production password sessions are disabled when Entra is active; the unverified legacy SSO
  attribute callback is unavailable in production.

### Azure OpenAI

- Azure OpenAI unified v1 endpoint support for chat completions and embeddings.
- Managed Identity is the production default; API keys are a local/break-glass mode only.
- Azure endpoint must use HTTPS unless an explicit local-development exception is set.
- EU-only routing accepts Azure only after an evidence-backed operator attestation.
- Provider response bodies are not propagated into application errors.
- Feature flags remain off by default and tenant policy is evaluated before provider selection.

### Application and browser security

- Trusted-host and explicit CORS allowlists.
- Production OpenAPI/Swagger/ReDoc exposure disabled.
- CSP, HSTS, frame, MIME-sniffing, referrer, permissions, opener and resource policies.
- Public metadata, robots, sitemap, web manifest and coordinated disclosure route.
- Production build gate for legal identity, privacy retention, security contact, host/auth boundary,
  public credential detection, global key prohibition, PII-block mode, Azure configuration and
  regional processing attestation.

### Delivery and supply chain

- Exact versions for the core Next.js/React toolchain and an override for the fixed PostCSS release.
- Node runtime constraint excludes unsupported Node 23.
- Immutable commit pins for third-party GitHub Actions.
- Backend lint/test/audit/SAST, frontend lint/test/build/audit, OPA tests, dependency review and
  CodeQL analysis in CI.
- Weekly dependency updates for Python, npm and GitHub Actions.

## Mandatory exit criteria

All items below require a named owner, dated evidence, reviewer, expiry/review date, and an accepted
residual-risk record. Production remains blocked until every item is closed.

1. **Enterprise identity boundary** — the Entra ID/OIDC code+PKCE flow, secure HttpOnly session,
   CSRF protection, session revocation, pre-provisioned `tid` + `oid` binding and app-role gate are
   implemented. Production still requires approved MFA/Conditional Access and lifecycle evidence,
   privileged-action step-up/claims challenges, a reviewed credential strategy, complete server-side
   route-family enforcement and removal of every browser API-key/direct tenant-ID trust path. Follow
   `docs/enterprise-entra-oidc-runbook.md`.
2. **Authorization and tenant isolation** — threat model and test every endpoint, background job,
   export, object store path, cache key and observability stream for cross-tenant access. Add negative
   integration tests against a production-equivalent Postgres deployment.
3. **Legal publication** — supply the real legal entity, representative, register, VAT and contact
   data; have qualified counsel approve imprint, privacy notice, terms, cookie/telemetry behavior,
   lawful bases, retention periods, international transfers and consumer/commercial applicability.
4. **GDPR operations** — approve RoPA, DPIA threshold and completed DPIA where required, TOMs,
   deletion/DSAR workflows, retention jobs, incident notification runbooks, DPA/SCC/TIA records,
   subprocessors, data classification, access reviews and evidence of execution.
5. **EU AI Act governance** — establish provider/deployer role per system, Article 4 literacy records,
   inventory and classification review, prohibited-practice controls, high-risk obligations where
   applicable, transparency/human-oversight procedures, logging, quality/risk management, post-market
   monitoring and incident processes. Automated output must remain advisory and reviewable.
6. **Azure landing zone** — document tenant/subscription/resource IDs, approved EU region or Data Zone,
   private networking, disabled public access where feasible, Managed Identity/RBAC, Key Vault,
   diagnostic settings, immutable/retained logs, backup/restore tests, CMK decision, budgets, Defender,
   policy assignments, model deployments, content filtering and modified-abuse-monitoring decision.
7. **Operational security** — approved SDL/threat model, vulnerability intake SLA, incident response,
   on-call/BCP/DR, RTO/RPO and restoration tests, patching, secrets rotation, access recertification,
   penetration test and remediation evidence.
8. **Product completion** — remove or implement NIS2 wizard stubs, mock connectors, placeholder export
   targets, filesystem-backed JSON stores and incomplete workflows. Replace temporary filesystem
   state with approved Postgres/Blob persistence and remove build-time live API fetches. No control may
   claim evidence from a simulated integration.
9. **Repository governance** — protect `main`, require pull requests, CODEOWNERS approval, signed or
   otherwise verified commits per policy, passing CI/CodeQL/dependency review, secret scanning and push
   protection. Select and publish an approved software license.
10. **Independent release review** — security, privacy, legal, AI governance and operations owners sign
    the same immutable release-evidence package. Re-run tests and scanning against the release commit
    and production configuration.

The current static frontend CSP still permits inline script/style execution for Next.js compatibility.
Before release, replace it with a reviewed nonce- or hash-based request-specific CSP and add browser
tests that prove both application behavior and policy enforcement.

## Open static-analysis findings

The full Bandit scan on 14 July 2026 reported zero high-severity findings and four medium-severity
findings. One is a high-confidence use of `xml.etree.ElementTree.fromstring` for XRechnung validation;
it must be replaced with a hardened parser and receive malicious-XML tests. Three low-confidence SQL
construction findings use migration/schema identifiers, but still require documented code review or
remediation rather than silent suppression. These findings predate the Entra change set and remain
production blockers until resolved or formally adjudicated with evidence.

## Azure deployment checklist

The application expects:

```text
COMPLIANCEHUB_FEATURE_LLM_ENABLED=false
COMPLIANCEHUB_LLM_PREFER_AZURE=true
COMPLIANCEHUB_LLM_ASSUME_AZURE_EU=false
COMPLIANCEHUB_LLM_PII_MODE=block
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=<approved-gpt-deployment>
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=<approved-embedding-deployment>
AZURE_OPENAI_AUTH=managed_identity
```

Keep LLM features disabled until the Azure evidence package and per-tenant policy are approved. The
EU attestation must only become `true` after verifying the concrete resource/deployment configuration
and applicable Microsoft terms; the variable does not create residency or compliance by itself.

## Decision

The hardening branch may proceed through review and test environments. It must not be presented as a
completed enterprise-compliance release, merged under weakened controls, or deployed to production
until the mandatory exit criteria are evidenced and independently approved.

## Primary references

- [Regulation (EU) 2024/1689 — EU AI Act](https://eur-lex.europa.eu/eli/reg/2024/1689/oj)
- [Regulation (EU) 2016/679 — GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/oj)
- [Directive (EU) 2022/2555 — NIS2](https://eur-lex.europa.eu/eli/dir/2022/2555/oj)
- [Azure OpenAI REST API](https://learn.microsoft.com/en-us/rest/api/microsoft-foundry/azureopenai/chat)
- [Azure authentication and endpoint migration](https://learn.microsoft.com/en-us/azure/developer/ai/how-to/switching-endpoints)
- [Data, privacy, and security for Azure Direct Models](https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/openai/data-privacy)
