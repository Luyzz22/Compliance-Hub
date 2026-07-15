# Azure runtime storage and CSP reporting — 15 July 2026

Status: application controls implemented and locally verified; Azure/Vercel infrastructure evidence,
restore testing, SIEM alerting and independent approval remain mandatory production gates.

## Control objective

Remove ephemeral `/tmp` persistence from the production trust model and make enforced CSP violations
observable without retaining full URLs, referrers, code samples, cookies, IP addresses or user-agent
strings. The implementation must not introduce Azure account keys, connection strings or other
long-lived storage credentials.

## Implemented application controls

### Durable runtime state

- The twelve former file stores use one server-only runtime-storage boundary.
- Development defaults to atomic local files with private directory/file modes. Local storage is
  rejected whenever `NODE_ENV=production` or `VERCEL` is present.
- Production accepts only `COMPLIANCEHUB_RUNTIME_STORAGE_BACKEND=azure_blob`.
- Azure-hosted workloads use `ManagedIdentityCredential`; Vercel workloads use the request-scoped
  Vercel OIDC assertion with Entra `ClientAssertionCredential`. `DefaultAzureCredential` is limited
  to non-production development.
- Account keys, shared-key credentials and connection strings are intentionally unsupported and
  rejected by a source gate.
- Blob clients are initialized lazily. Containers are never created by application code; lifecycle,
  region, network and access policy remain controlled infrastructure concerns.
- Vercel Functions are pinned by version-controlled project configuration to Frankfurt (`fra1`),
  replacing the platform default `iad1`. No cross-region Function failover is configured.
- Whole-document writes use Azure Block Blobs. Lead event lines use Append Blobs. Distributed
  read-modify-write sections use 60-second Azure Blob leases with bounded acquisition retries.
- Object keys use a fixed validated prefix. Paths outside the application root are hashed before
  mapping, so host filesystem structure is not disclosed in Blob names.
- Reads and writes have explicit size ceilings. Missing objects are distinguished from configuration,
  service and malformed-JSON errors; only genuine absence may become an empty initial state.
- The prebuild gate checks all twelve stores, required pinned SDKs, passwordless modes, lease/append
  invariants and forbidden long-lived credential paths.

### CSP violation reporting

- Enforced production CSP now declares both `report-to csp-endpoint` and the compatibility
  `report-uri /api/security/csp-report` directive. `Reporting-Endpoints` maps the named group to the
  same-origin endpoint and is preserved on redirects.
- The endpoint accepts only `application/csp-report` and `application/reports+json`, limits each
  request to 16 KiB and at most ten CSP records, and rejects malformed or unrelated reports.
- Reports are treated as attacker-controlled. The structured security event contains only the
  effective directive, enforcement disposition, HTTP status, document origin, blocked-resource
  origin/class and source origin. Paths, queries, fragments, referrers, original policies, line
  numbers and code samples are discarded before logging.
- Responses are bodyless and `private, no-store`. The endpoint ignores authentication context and
  does not write reports into product-state blobs.

## Production configuration

Server-only variables:

```text
COMPLIANCEHUB_RUNTIME_STORAGE_BACKEND=azure_blob
COMPLIANCEHUB_RUNTIME_STORAGE_AUTH=vercel_oidc  # Vercel; managed_identity on Azure hosting
COMPLIANCEHUB_RUNTIME_STORAGE_PREFIX=compliancehub/runtime/v1
AZURE_STORAGE_ACCOUNT_NAME=<approved-account>
AZURE_STORAGE_CONTAINER_NAME=<pre-provisioned-private-container>
AZURE_TENANT_ID=<entra-tenant-guid>              # required for vercel_oidc
AZURE_CLIENT_ID=<federated-app-or-managed-identity-client-id>
COMPLIANCEHUB_RUNTIME_STORAGE_READY=false
COMPLIANCEHUB_CSP_REPORTING_READY=false
```

Do not create or commit `VERCEL_OIDC_TOKEN`; Vercel supplies the short-lived assertion to Functions.
Do not set either readiness attestation to `true` until the evidence below has named approval.

## Required Azure and Vercel evidence

1. Record the Azure tenant, subscription, resource group, storage resource ID, region and data
   residency decision. Map the service and Microsoft/Vercel roles in the RoPA/DPIA and subprocessor
   register.
2. Provision a private container. Disable anonymous Blob access and Shared Key authorization. Apply
   the narrowest reviewed Blob data-plane RBAC scope to the workload identity.
3. Decide and evidence public-network denial/private endpoints, DNS and the actual connectivity path.
   A Vercel Function cannot reach an Azure private endpoint without an approved network design.
4. For Vercel, configure an Entra federated identity credential whose issuer, audience and exact
   production subject match the Vercel team/project/environment claims. Use a separate identity and
   container/prefix for Preview; Preview must never receive Production data access.
5. Configure encryption, CMK decision, versioning/soft delete, backup, retention and deletion. Perform
   and timestamp a restore test against representative objects; record RPO/RTO and owners.
6. Enable Azure diagnostic settings and Vercel log draining to the approved EU SIEM. Alert on storage
   authentication/authorization failures, lease timeouts, CSP `script-src*` violations, sustained
   report volume and reporting-endpoint abuse. Prove alert delivery and on-call ownership.
7. Apply WAF/rate limits to the intentionally public CSP endpoint. Approve CSP-report retention and
   access, and verify that downstream processors do not enrich the minimized event with request
   cookies, raw IPs or other identifiers unless a separately approved lawful basis requires it.

## Verification evidence

- Unit tests cover local atomic write/append/read, production fail-closed behavior, passwordless mode
  selection, traversal-free Blob keys, missing-object semantics, in-memory Azure Block/Append Blob
  operations and concurrent local/Azure lock serialization.
- CSP tests cover legacy and Reporting API formats, data minimization, media-type/JSON/size rejection,
  bodyless responses and reporting headers on normal responses and redirects.
- All 284 frontend tests in 80 files and all 1,545 backend tests passed. ESLint, TypeScript, Ruff and
  Ruff format checks passed; Bandit reported zero findings across `app` and `scripts`.
- The Next.js 16.2.10 production build completed without warnings. npm audit and pip-audit reported no
  known third-party vulnerabilities; the unpublished local `compliancehub` package was the expected
  pip-audit skip.
- The production browser rendered meaningful content, changed to the NIS2 product tab, showed no
  framework overlay or console/page errors before the deliberate CSP probe, and carried nonces on all
  26 scripts. The injected inline style remained unapplied.
- Live local headers contained the enforced reporting directives and named endpoint. A browser-origin
  same-origin report POST returned bodyless HTTP 204; the server event retained only
  `style-src-attr`, the document origin, `inline`, enforcement disposition and status code. Injected
  query email and sample data were absent from the event.
- The first immutable Preview audit exposed Vercel default Function placement in Washington, D.C.
  (`iad1`). The repository now pins `fra1`; the replacement Preview deployment metadata must show
  every generated Function in `fra1` before this item is considered closed.
- The CI readiness helper's generic `urlopen` call was replaced with an HTTP(S)-only, HTTPS-by-default,
  non-redirecting, size-bounded client. Path/query inputs are encoded and seven negative tests cover
  unsafe schemes, credentials, fragments, remote plain HTTP and injection-shaped identifiers.

## Residual limits and release decision

- No live Azure account was changed or queried in this wave. Unit-level adapter evidence does not
  prove region, network controls, Entra federation, RBAC, encryption, diagnostics or restoreability.
- Azure Blob makes the state durable but does not turn multi-tenant JSON documents into a relational,
  row-isolated system. Lead, job and mutable portfolio state still require a planned migration to the
  governed Postgres domain model for high concurrency, queryability, tenant-scoped retention and
  database-level authorization.
- CSP reporting is best-effort and cannot be the sole incident-detection channel.
- Production release remains blocked until both readiness attestations are backed by immutable
  operator evidence and security/privacy/operations approval. This document is engineering evidence,
  not a GDPR or EU AI Act certification.

## Primary references

- [Azure Blob Storage with JavaScript and DefaultAzureCredential](https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blob-javascript-get-started)
- [Authorize Blob access with Microsoft Entra ID](https://learn.microsoft.com/en-us/azure/storage/blobs/authorize-access-azure-active-directory)
- [Azure Blob security recommendations](https://learn.microsoft.com/en-us/azure/storage/blobs/security-recommendations)
- [Vercel OIDC federation](https://vercel.com/docs/oidc)
- [Vercel OIDC Azure client-assertion reference](https://vercel.com/docs/oidc/reference)
- [W3C Content Security Policy Level 3](https://www.w3.org/TR/CSP/)
- [W3C Reporting API](https://www.w3.org/TR/reporting-1/)
