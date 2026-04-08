# Identity, Registration, Profile & Role-Based Access

> Enterprise-grade identity, profile, and registration system for ComplianceHub —
> DACH/EU compliance-ready with DSGVO, NIS2, and GoBD audit-trail support.

## Overview

ComplianceHub's identity module provides:

- **User Registration** with email + password and verification flow
- **Login / Logout** with lockout protection and rate limiting
- **Password Reset** via secure time-limited tokens
- **Profile Management** (name, company, language, timezone)
- **Tenant-Specific Roles** (M:N user ↔ tenant assignments)
- **SBS Domain Auto-Admin** for verified `@sbsdeutschland.de` / `@sbsdeutschland.com` emails
- **Audit Logging** for all security-relevant events (GoBD hash-chain)
- **SSO Readiness** via `sso_provider` / `sso_subject` fields (SAML 2.0 / OIDC prepared)

## Architecture

### Data Model

```
┌─────────────┐       ┌──────────────────────┐
│   users      │  1:N  │ user_tenant_roles     │
├─────────────┤       ├──────────────────────┤
│ id (PK)     │◄──────│ user_id (FK)         │
│ email       │       │ tenant_id            │
│ password_   │       │ role                 │
│   hash      │       │ assigned_by          │
│ display_    │       │ created_at_utc       │
│   name      │       │ updated_at_utc       │
│ company     │       └──────────────────────┘
│ language    │
│ timezone    │
│ email_      │
│   verified  │
│ sso_        │
│   provider  │
│ sso_subject │
│ ...         │
└─────────────┘
```

### Roles

| Role               | Key Permissions                                   |
|--------------------|---------------------------------------------------|
| `VIEWER`           | Read-only dashboard, AI systems, compliance status |
| `CONTRIBUTOR`      | Viewer + risk register, incidents, audit log       |
| `EDITOR`           | Contributor + edit AI systems, risk register       |
| `AUDITOR`          | Contributor + export audit logs                    |
| `COMPLIANCE_OFFICER` | Editor + manage incidents, policies, reports     |
| `COMPLIANCE_ADMIN` | Same as COMPLIANCE_OFFICER                         |
| `CISO`             | Same as COMPLIANCE_OFFICER                         |
| `BOARD_MEMBER`     | Dashboard, reports, compliance status              |
| `TENANT_ADMIN`     | Full tenant management (users, settings, keys)     |
| `SUPER_ADMIN`      | All permissions across all tenants                 |

### SBS Domain Auto-Admin Logic

Located in `app/services/sbs_domain_auto_admin.py`:

1. **Only verified emails** qualify for auto-admin assignment
2. `ki@sbsdeutschland.de` → `SUPER_ADMIN` (bootstrap)
3. Other `@sbsdeutschland.de` or `@sbsdeutschland.com` → `TENANT_ADMIN`
4. Non-SBS domains → no auto-assignment

## API Endpoints

### Public (No Auth Required)

| Method | Endpoint                              | Description                |
|--------|---------------------------------------|----------------------------|
| POST   | `/api/v1/auth/register`               | Register new user          |
| POST   | `/api/v1/auth/verify-email?token=...` | Verify email address       |
| POST   | `/api/v1/auth/login`                  | Authenticate user          |
| POST   | `/api/v1/auth/password-reset/request` | Request password reset     |
| POST   | `/api/v1/auth/password-reset/confirm` | Confirm password reset     |

### Protected (API Key + Tenant Required)

| Method | Endpoint                            | Permission     | Description          |
|--------|-------------------------------------|----------------|----------------------|
| GET    | `/api/v1/auth/profile/{user_id}`    | Authenticated  | Get user profile     |
| PUT    | `/api/v1/auth/profile/{user_id}`    | Authenticated  | Update user profile  |
| POST   | `/api/v1/auth/roles/assign`         | MANAGE_USERS   | Assign role to user  |
| GET    | `/api/v1/auth/users`                | MANAGE_USERS   | List tenant users    |

## Frontend Pages

| Route                  | Description              |
|------------------------|--------------------------|
| `/auth/register`       | User registration form   |
| `/auth/login`          | Login form               |
| `/auth/forgot-password`| Password reset request   |
| `/auth/reset-password` | Password reset confirm   |
| `/auth/profile`        | Profile & account settings|

## Password Policy

- Minimum 10 characters
- Must contain uppercase, lowercase, and digit
- Account lockout after 5 failed attempts (15 min cooldown)
- Reset tokens expire after 1 hour

## Audit Events

All auth events are logged to the immutable `audit_logs` table with GoBD hash-chain:

| Action                          | Trigger                        |
|---------------------------------|--------------------------------|
| `user.registered`               | New user registration          |
| `user.email_verified`           | Email verification completed   |
| `user.login`                    | Successful login               |
| `user.password_reset_requested` | Password reset requested       |
| `user.password_reset`           | Password successfully reset    |
| `user.profile_updated`          | Profile changes saved          |
| `user.role_assigned`            | Role assigned/changed          |

## DSGVO / Privacy

- **Data Minimisation**: Only essential fields stored (email, display name, company)
- **No tracking cookies**: Pure API-based authentication
- **Deletion ready**: User data isolated and deletable per tenant
- **Audit-only hashes**: Passwords stored as hashes only

## SSO Readiness

The `UserDB` model includes:
- `sso_provider` (VARCHAR 64) — e.g., `azure_ad`, `sap_ias`, `saml2`
- `sso_subject` (VARCHAR 255) — external identity provider subject ID

These fields enable future SAML 2.0 / OIDC integration without schema changes.

## Database Migration

Migration `20260407_add_users_and_roles` creates:
- `users` table with indexes on `email`
- `user_tenant_roles` table with indexes on `user_id` and `tenant_id`
- Unique constraint on `(user_id, tenant_id)` for role assignments

## Testing

Tests in `tests/test_identity_and_sbs_auto_admin.py` cover:

- **Unit**: SBS domain matching, auto-role assignment, password policy
- **Integration**: Registration, verification, login, password reset, profile, role assignment
- **Negative**: Unverified SBS email, non-SBS domains, cross-tenant escalation
