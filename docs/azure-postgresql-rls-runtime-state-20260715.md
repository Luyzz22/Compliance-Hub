# Azure PostgreSQL RLS runtime-state wave — 2026-07-15

## Outcome and scope

This wave introduces the first normalized, tenant-governed PostgreSQL slice for the Next.js runtime:

- `advisor_mandant_history`: one versioned row per tenant for export and review history.
- `advisor_mandant_reminders`: one versioned row per reminder, with tenant, status, due date,
  source and bounded note fields.
- `runtime_state_deletion_audit`: payload-free, append-only deletion evidence.

The two stores use Azure Database for PostgreSQL in production and keep the existing file/blob path
only for local development and tests. Production has no database-to-blob fallback. This prevents
split-brain writes and makes a failed database configuration visible instead of silently losing
governance state.

This is a technical control increment, not a declaration of GDPR, EU AI Act, ISO 27001 or BSI
certification. Ten other Next.js runtime stores remain behind the Azure Blob boundary and require
separate domain migrations.

## Security model

The versioned migration is
`db/postgres/migrations/20260715_advisor_runtime_state_rls.sql`.

- Objects live in `compliancehub_private`; `PUBLIC` has no schema or table access.
- The runtime roles are `NOLOGIN`, `NOSUPERUSER` and `NOBYPASSRLS`.
- Tenant principals inherit `compliancehub_runtime_app`.
- The advisor platform principal inherits `compliancehub_runtime_platform_app`, which in turn
  inherits the base runtime role.
- Both domain tables and the deletion audit table use `ENABLE ROW LEVEL SECURITY` and
  `FORCE ROW LEVEL SECURITY`.
- Tenant access requires a transaction-local `compliancehub.tenant_id` match.
- Platform access additionally requires membership in `compliancehub_runtime_platform_app`.
  Setting `compliancehub.platform_access=true` alone cannot elevate a tenant role.
- Queries also contain explicit tenant predicates where a tenant identifier is available. RLS is
  defense in depth, not a replacement for application authorization.
- Deletion is rejected unless transaction-local actor and approved-reason context exist. A
  security-definer trigger writes only record identity, tenant, actor, reason, time and row version
  to the audit table; deleted row payloads are not duplicated.
- `retention_until` and `legal_hold` exist on both domain tables. Closed reminders and updated
  history rows receive the approved `COMPLIANCEHUB_ADVISOR_RUNTIME_RETENTION_DAYS` window. There is
  no unattended purge until the retention schedule and legal-hold process are approved.

The CI database job runs PostgreSQL 17.9 from a digest-pinned image, applies the migration twice to
prove idempotency, and executes real cross-tenant denial, self-elevation, platform-scope and deletion
audit tests.

## Software supply-chain observation

The dependency graph is lockfile-pinned and the dependency review rejects newly introduced known
vulnerabilities at moderate severity or above. At review time, npm audit reported no known
vulnerability. GitHub's OpenSSF enrichment nevertheless reported scores below the repository's
informational threshold of 3 for the transitive `pg-types` packages `pg-int8@1.0.1`,
`postgres-array@2.0.0`, `postgres-bytea@1.0.1` and `xtend@4.0.2`. A low Scorecard value is not a
vulnerability finding, but it is a supplier-maintenance signal and is not suppressed here.

Production therefore also requires `COMPLIANCEHUB_POSTGRES_SUPPLY_CHAIN_READY=true` after the
software bill of materials, package provenance, licenses, maintenance status and available client
alternatives have been reviewed and the decision has been linked from the release record. Any
future advisory still fails the existing dependency and audit gates according to severity.

## Passwordless connection boundary

The application never accepts a PostgreSQL password or connection string. It connects only to a
validated `*.postgres.database.azure.com` hostname on port 5432, verifies the TLS certificate and
uses a dynamic Microsoft Entra token for the Azure OSS RDBMS scope. Pools are small, lazy, bounded
and rotate connections after 30 minutes so newly created connections obtain fresh tokens.

- Vercel: `ClientAssertionCredential` exchanges the Vercel OIDC assertion through the configured
  Entra federated credential.
- Azure hosting: `ManagedIdentityCredential`.
- `DefaultAzureCredential` remains development-only and is rejected in production.

Microsoft documents that Entra access tokens are passed as the PostgreSQL password and should be
obtained shortly before connection. Node-postgres supports synchronous or asynchronous dynamic
password callbacks. Primary references:

- <https://learn.microsoft.com/en-us/azure/postgresql/security/security-entra-configure>
- <https://learn.microsoft.com/en-us/azure/postgresql/security/security-manage-entra-users>
- <https://learn.microsoft.com/en-us/azure/postgresql/security/security-access-control>
- <https://node-postgres.com/features/connecting>
- <https://node-postgres.com/features/ssl>

## Infrastructure provisioning and role binding

Do not run the application as the PostgreSQL or Entra administrator.

1. Provision Azure Database for PostgreSQL Flexible Server in the approved EU region and record the
   resource ID, subscription, tenant, region and responsible owner.
2. Enable Microsoft Entra-only authentication after the documented break-glass account and recovery
   procedure have been approved.
3. Use a dedicated Entra administrator group for migrations. Do not use this group for runtime.
4. Apply the migration with the migration principal and retain its immutable log and checksum.
5. Map the Vercel/Azure application service principal by object ID. Replace placeholders only after
   independently confirming the Enterprise Application object ID:

   ```sql
   SELECT *
   FROM pg_catalog.pgaadauth_create_principal_with_oid(
       '<runtime-role-name>',
       '<service-principal-object-id>',
       'service',
       FALSE,
       FALSE
   );

   GRANT compliancehub_runtime_platform_app TO "<runtime-role-name>";
   ALTER ROLE "<runtime-role-name>"
       NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
   ```

6. Set `AZURE_POSTGRES_USER` to the exact mapped PostgreSQL role name. Never use `postgres`,
   `azure_pg_admin` or `azuresu`.
7. Prefer private connectivity. If the approved topology requires a public endpoint, restrict it to
   controlled egress, enable the Azure firewall evidence trail and document the residual risk.
8. Enable diagnostic logs, database audit logs, Defender/monitoring alerts and a security-approved
   log destination without query parameters or row payloads.
9. Configure zone redundancy/high availability as required by the BIA, PITR retention, backup
   redundancy and a recurring restore test into an isolated environment.

## Required production configuration

```dotenv
COMPLIANCEHUB_RELATIONAL_RUNTIME_BACKEND=azure_postgres
AZURE_POSTGRES_HOST=<approved-server>.postgres.database.azure.com
AZURE_POSTGRES_PORT=5432
AZURE_POSTGRES_DATABASE=compliancehub
AZURE_POSTGRES_USER=<mapped-entra-runtime-role>
COMPLIANCEHUB_ADVISOR_RUNTIME_RETENTION_DAYS=<approved-30-to-3650>

COMPLIANCEHUB_RUNTIME_STORAGE_AUTH=vercel_oidc
AZURE_TENANT_ID=<tenant-guid>
AZURE_CLIENT_ID=<federated-service-principal-client-guid>

COMPLIANCEHUB_RELATIONAL_RUNTIME_READY=false
COMPLIANCEHUB_POSTGRES_RLS_READY=false
COMPLIANCEHUB_POSTGRES_NETWORK_READY=false
COMPLIANCEHUB_POSTGRES_BACKUP_RESTORE_READY=false
COMPLIANCEHUB_POSTGRES_RETENTION_READY=false
COMPLIANCEHUB_POSTGRES_DATA_MIGRATION_READY=false
COMPLIANCEHUB_POSTGRES_SUPPLY_CHAIN_READY=false
```

For Azure-hosted execution use `managed_identity` instead of `vercel_oidc`. Do not set any of
`AZURE_POSTGRES_PASSWORD`, `PGPASSWORD`, `POSTGRES_URL` or `DATABASE_URL` in the frontend runtime.

Each readiness flag is an attestation, not a feature switch. It may be set to `true` only after the
named evidence has been reviewed and linked from the change/release record.

## Source-data migration and cutover

The previous Azure Blob data must not be ignored or dual-written indefinitely.

1. Freeze advisor-history/reminder mutations for a documented maintenance window.
2. Export the two source objects with version/ETag, byte length and SHA-256 checksum. Retain the
   source objects read-only until rollback expiry.
3. Validate every tenant identifier, reminder UUID, enum, note length and timestamp offline. Reject
   the entire import on any malformed record; do not silently skip it.
4. Load into isolated staging tables, then transform into the domain tables in one transaction with
   the platform actor context set to the migration change ID.
5. Reconcile source and target:
   - exact tenant-history count;
   - exact reminder count by tenant/status/category/source;
   - maximum timestamps per tenant;
   - deterministic canonical-row checksums excluding database-managed timestamps and row versions.
6. Execute tenant A/B isolation probes using the actual runtime role, plus a platform aggregate read.
7. Set `COMPLIANCEHUB_POSTGRES_DATA_MIGRATION_READY=true` only after the reconciliation evidence and
   rollback decision are independently approved.
8. Switch `COMPLIANCEHUB_RELATIONAL_RUNTIME_BACKEND` once. Run post-cutover read/write probes and
   monitor database errors, latency, connection count and RLS denials.
9. Roll back by restoring the previous deployment and source blobs only if no PostgreSQL write has
   been accepted. After the first accepted write, use the incident runbook and a reviewed reverse
   migration; never merge two authorities automatically.

## Governed retention execution

No application endpoint can hard-delete these records. An approved operator may delete expired,
non-held rows only through a reviewed migration/maintenance transaction that sets both contexts:

```sql
BEGIN;
SELECT set_config('compliancehub.actor_id', '<approved-operator-or-job>', TRUE);
SELECT set_config('compliancehub.deletion_reason', '<ticket-and-policy-reference>', TRUE);
SELECT set_config('compliancehub.platform_access', 'true', TRUE);
SELECT set_config('compliancehub.tenant_id', '__platform__', TRUE);

DELETE FROM compliancehub_private.advisor_mandant_reminders
WHERE reminder_id IN (
    SELECT reminder_id
    FROM compliancehub_private.advisor_mandant_reminders
    WHERE retention_until <= clock_timestamp()
      AND legal_hold = FALSE
    ORDER BY retention_until
    LIMIT 500
    FOR UPDATE SKIP LOCKED
);
COMMIT;
```

Use the equivalent tenant-key selection for history only when the approved policy permits deletion
of the complete tenant history. Reconcile every batch with `runtime_state_deletion_audit` and the
change ticket.

## Evidence required before production

- Azure resource/region and data-flow record.
- Entra-only authentication and federated-credential evidence.
- Runtime principal membership, `NOBYPASSRLS`, nonownership and least-privilege grants.
- Migration checksum/log and PostgreSQL version compatibility result.
- Actual-runtime-role tenant isolation and self-elevation negative tests.
- Private-network/firewall/DNS/TLS evidence.
- HA, PITR and successful isolated restore evidence with measured RPO/RTO.
- Approved retention schedule, legal-hold workflow and deletion-audit sample.
- Source-to-target reconciliation and rollback decision.
- PostgreSQL client SBOM and documented review of the transitive OpenSSF maintenance signals.
- SIEM routing, alerts, on-call ownership and incident drill.
- Independent application-security, database, privacy and operations approval.

Until all evidence exists, the production release gate intentionally remains closed.
