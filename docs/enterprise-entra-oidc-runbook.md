# Microsoft Entra ID OIDC — Enterprise deployment runbook

Status: implementation complete, production enablement blocked pending external evidence
Control owner: Identity & Access Management
Reviewers: Security, Privacy, Platform Operations
Review cadence: before every identity change and at least quarterly

## Security objective

ComplianceHub uses a tenant-specific Microsoft Entra ID confidential web application and the
OAuth 2.0 authorization-code flow with PKCE. The browser receives only an opaque, revocable
ComplianceHub session in a `Secure`, `HttpOnly`, `SameSite=Strict`, production `__Host-` cookie.
OIDC state, nonce and PKCE verifier are short-lived and authenticated-encrypted in a separate
`HttpOnly`, `SameSite=Lax` transaction cookie so the top-level Entra redirect can complete.

Authorization is fail-closed:

- the Next.js BFF and Python API independently validate the identity response;
- the API accepts only RS256 and validates signature, tenant-specific issuer, audience, expiry,
  not-before time, issued-at time, nonce, token version and immutable `tid` + `oid` identifiers;
- access requires an Entra application role and an explicit, pre-provisioned local identity link;
- the local tenant membership and local role remain the source of application authorization;
- e-mail, display name, browser tenant headers and browser role headers never grant access;
- production password sessions and the legacy attribute callback are disabled when Entra is active.

## 1. Create the Entra application

Create a **single-tenant** app registration in the approved Azure tenant. Configure a Web redirect
URI with an exact match:

```text
https://<approved-app-origin>/api/auth/entra/callback
```

Do not configure implicit grant or hybrid-flow tokens. Record the Entra tenant ID, application
(client) ID, object owner, purpose, data classification and review date in the controlled asset
register.

Create an application role such as `ComplianceHub.Access`, allowed for users/groups. Assign it only
through governed Entra groups or direct assignments approved by IAM. The provider configuration in
ComplianceHub must contain the exact required role:

```json
{
  "required_app_roles": ["ComplianceHub.Access"]
}
```

The configured issuer must be tenant-specific:

```text
https://login.microsoftonline.com/<entra-tenant-id>/v2.0
```

## 2. Configure credentials and secrets

The current BFF supports an Entra client secret. Store it only in the approved deployment secret
store; never commit it, expose it as `NEXT_PUBLIC_*`, place it in support tickets, or paste it into
chat. Use separate credentials per environment, minimum privilege and documented rotation.

For production, the architecture review board must decide whether to replace the client secret with
a certificate credential or workload identity. Until that decision, implementation and rotation
test are approved, the G3/G4 identity gate remains closed.

Generate independent high-entropy values for the BFF trust boundary and OIDC transaction encryption.
Do not reuse the Entra credential.

```text
COMPLIANCEHUB_ENTRA_ENABLED=true
COMPLIANCEHUB_ENTRA_TENANT_ID=<non-placeholder-guid>
COMPLIANCEHUB_ENTRA_CLIENT_ID=<non-placeholder-guid>
COMPLIANCEHUB_ENTRA_CLIENT_SECRET=<secret-store-reference/value>
COMPLIANCEHUB_ENTRA_PROVIDER_ID=<local-provider-guid>
COMPLIANCEHUB_AUTH_TRANSACTION_SECRET=<independent-random-secret-min-32-bytes>
COMPLIANCEHUB_BFF_SHARED_SECRET=<independent-random-secret-min-32-characters>
COMPLIANCEHUB_APP_ORIGIN=https://<approved-app-origin>
COMPLIANCEHUB_ENTRA_CONDITIONAL_ACCESS_READY=false
COMPLIANCEHUB_ENTRA_PROVISIONING_READY=false
COMPLIANCEHUB_ALLOW_LEGACY_SSO_CALLBACK=false
```

The two `*_READY` attestations may be set to `true` only after the referenced evidence is reviewed,
dated and linked to the release record. Environment variables do not constitute evidence.

## 3. Provision identities

Create the local user, verify/activate it, and assign exactly one approved role in the intended local
tenant. Create the enabled OIDC provider for that same tenant. An authorized tenant administrator
then links the local user to the immutable Entra directory identifiers:

```http
POST /api/v1/enterprise/identity-providers/<provider-id>/entra-links
Content-Type: application/json

{
  "user_id": "<local-user-id>",
  "entra_tenant_id": "<tid>",
  "entra_object_id": "<oid>"
}
```

Do not link by e-mail. Both duplicate Entra principals and attempts to link a user across local
tenants are rejected. Until SCIM or an approved event-driven lifecycle connector exists, every
joiner/mover/leaver action requires a dual-controlled ticket and audit evidence.

## 4. Conditional Access and privileged access

Before production, Security/IAM must provide evidence that the enterprise application is covered by
approved Conditional Access controls, including MFA strength, compliant-device/location decisions,
session lifetime and break-glass exclusions. Break-glass accounts must be separately monitored and
tested. Privileged roles require a documented step-up design; the present session proves primary
Entra authentication but does not yet implement per-action claims challenges.

Set `COMPLIANCEHUB_ENTRA_CONDITIONAL_ACCESS_READY=true` only after the policy export, assignment,
exclusion review, negative test and named approval are in the release evidence pack.

## 5. Release verification

Execute against a production-equivalent environment:

1. Valid assigned user reaches only the linked local tenant and role.
2. Unassigned app role, disabled provider, unlinked `tid` + `oid`, wrong tenant, wrong audience,
   expired/not-yet-valid token, reused state and wrong nonce all fail.
3. A browser-supplied tenant or role cannot change authorization.
4. Password login and `/api/v1/enterprise/sso/callback` return `410` in the production policy.
5. Logout, membership removal, role change and user disablement revoke existing access.
6. Session and identity tokens are absent from browser JavaScript, URLs, logs, analytics and audit
   metadata.
7. Monitoring detects repeated callback failures, role/provisioning failures and break-glass use
   without recording raw tokens or personal claim payloads.
8. Credential rotation and rollback are executed, timed and attached to the evidence pack.

Run repository verification and retain the immutable results for the release commit:

```bash
.venv/bin/ruff check app tests
.venv/bin/pytest -q
cd frontend
npm run lint
npm run test:unit
npm audit --audit-level=high
npm run build
```

The production build must also pass `npm run verify:enterprise` with the reviewed deployment
configuration. Never weaken or bypass this gate to obtain a deployment.

## 6. Rollback and incident handling

Rollback means disabling the affected Entra application/provider, revoking ComplianceHub sessions,
rotating exposed credentials and restoring the last approved release. Do not re-enable password
login as an unreviewed production fallback. IAM, incident command and the DPO/legal reviewer assess
notification obligations and preserve metadata-only evidence under the approved retention policy.

## Required production evidence

- app registration manifest, owners, redirect URIs and app-role assignments;
- Conditional Access policy export and test results;
- joiner/mover/leaver and quarterly access-recertification evidence;
- credential storage, rotation and certificate/workload-identity decision;
- threat model, cross-tenant negative tests and production-like login/logout evidence;
- alert rules, incident/break-glass exercise and session-revocation evidence;
- security, privacy and operations approvals with expiry/review dates.

Production remains blocked while any item is absent or an open critical/high finding exists.

## Primary implementation references

- [Microsoft identity platform: authorization-code flow and PKCE](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow)
- [Microsoft identity platform: validate tokens](https://learn.microsoft.com/en-us/entra/identity-platform/claims-validation)
- [Microsoft Entra application roles](https://learn.microsoft.com/en-us/entra/identity-platform/howto-add-app-roles-in-apps)
- [Microsoft identity platform ID-token claims](https://learn.microsoft.com/en-us/entra/identity-platform/id-token-claims-reference)
- [Microsoft identity platform claims challenges](https://learn.microsoft.com/en-us/entra/identity-platform/claims-challenge)
