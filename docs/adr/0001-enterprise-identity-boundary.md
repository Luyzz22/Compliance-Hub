# ADR 0001: Enterprise identity and browser trust boundary

- Status: accepted for implementation
- Date: 2026-07-14
- Decision owners: executive sponsor, architecture review board, security/privacy reviewers
- Review trigger: before G3 pre-production and on any identity-provider change

## Context

The prototype lets browser code send a bearer API key and a tenant identifier. The password login
validates credentials but does not create a durable, revocable browser session. Some authorization
checks trust a client-supplied role header. This is incompatible with an enterprise tenant boundary.

## Decision

1. The browser communicates only with same-origin Next.js BFF endpoints.
2. The BFF stores an opaque backend session token in a `Secure`, `HttpOnly`, `SameSite=Strict`,
   production `__Host-` cookie. The raw token is never returned to browser JavaScript or persisted
   by the backend.
3. The backend stores only a SHA-256 lookup digest of the high-entropy token and binds the session to
   one user, one tenant, one normalized enterprise role, authentication method and expiry.
4. Every backend request resolves tenant and role from the authenticated session. A supplied tenant
   header must match the session; client role headers are ignored unless an explicit non-production
   compatibility flag is enabled.
5. Mutating BFF requests require same-origin validation and a double-submit CSRF token. Session
   rotation, revocation and last-seen metadata are server responsibilities.
6. Microsoft Entra ID OIDC is the target production identity provider. Password authentication is a
   transitional local/test path and must be disabled for production after Entra integration.
7. Proxy redirects are convenience and defense-in-depth only. Server Components, Route Handlers and
   backend dependencies independently revalidate authentication and authorization.

## Rejected options

- Public `NEXT_PUBLIC_API_KEY`: bearer secrets cannot be protected in browser bundles.
- Tenant selection from a cookie/header without membership verification: enables horizontal access.
- Proxy-only authorization: vulnerable to routing/proxy bypass and does not protect direct APIs.
- Long-lived JWT without a revocation registry: unacceptable for privileged access and leaver events.
- Self-asserted role headers: roles must originate from a governed user/tenant assignment.

## Exit criteria

- invalid, expired and revoked sessions fail with 401;
- tenant mismatch fails with 403 before repository access;
- role spoofing does not change authorization;
- logout revokes the backend session and deletes both cookies;
- session and CSRF tokens never appear in browser-facing response bodies, logs or audit metadata;
- negative tests cover cross-tenant reads/writes and all privileged route families;
- production gate detects every remaining browser credential path and remains closed until none exist.

## Implementation evidence — 2026-07-14

- Backend sessions are stored as SHA-256 token digests and invalidated on logout, password reset,
  identity disablement, tenant-membership removal and role change.
- The BFF login, session and logout routes use no-store responses, authenticated backend-to-BFF
  calls, origin validation and double-submit CSRF for mutations.
- The authenticated catch-all gateway revalidates the backend session, derives the tenant from the
  principal and strips browser-supplied credential, tenant and role assertions.
- Protected page namespaces use an optimistic proxy redirect; the Executive Dashboard and backend
  gateway independently revalidate the session on the server.
- Negative tests cover tenant mismatch, role spoofing, self-only profile access, revocation,
  verification, multi-tenant selection, BFF authentication, origin and CSRF rejection.
- The Entra integration uses tenant-specific authorization code + PKCE, authenticated-encrypted
  state/nonce transactions and independent Next.js/API token checks. The API allowlists RS256 and
  validates signature, issuer, audience, time claims, nonce, token version and immutable `tid` +
  `oid` claims.
- Entra access requires both an assigned application role and an administrator-provisioned identity
  link. Local tenant membership and role remain authoritative; mutable e-mail claims never grant
  access.
- Production policy disables password sessions when Entra is enabled and permanently disables the
  legacy attribute callback. The production build gate requires Entra configuration, Conditional
  Access and provisioning attestations and rejects placeholder identifiers.
- The operator procedure and evidence requirements are defined in
  `docs/enterprise-entra-oidc-runbook.md`.

## Residual production blockers

- Microsoft Entra ID OIDC is implemented but not production-enabled. Tenant/app registration,
  MFA/Conditional Access, governed app-role assignment, joiner/mover/leaver evidence and access
  recertification require external configuration and named approval.
- The current BFF supports an Entra client secret. The architecture review board must approve and
  test its storage/rotation or complete a certificate/workload-identity credential design before
  G3/G4.
- Step-up authentication for individual privileged actions and claims-challenge handling remains an
  explicit production blocker.
- All legacy Next.js route families and Server Components must be migrated to the session helpers
  and receive route-family authorization tests before the auth-readiness attestation may be true.
- Login abuse controls still require Azure Front Door/WAF rate limits, alerting and a tested
  break-glass process.
- Expired-session purge/retention, access recertification and leaver-event evidence require an
  operated scheduled control.
