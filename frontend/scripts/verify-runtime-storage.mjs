import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const errors = [];
const runtimeBoundary = readFileSync(resolve("src/lib/runtimeFileIO.ts"), "utf8");
const postgresBoundary = readFileSync(resolve("src/lib/runtimePostgres.ts"), "utf8");
const advisorPostgresStore = readFileSync(
  resolve("src/lib/advisorRuntimePostgresStore.ts"),
  "utf8",
);
const postgresMigration = readFileSync(
  resolve("../db/postgres/migrations/20260715_advisor_runtime_state_rls.sql"),
  "utf8",
);
const postgresContractTest = readFileSync(
  resolve("../tests/postgres/advisor_runtime_state_rls_test.sql"),
  "utf8",
);
const packageJson = JSON.parse(readFileSync(resolve("package.json"), "utf8"));
const stores = [
  "advisorEvidenceHookStore.ts",
  "advisorKpiHistoryStore.ts",
  "advisorMandantHistoryStore.ts",
  "advisorMandantReminderStore.ts",
  "advisorSlaSignalStateStore.ts",
  "boardReadinessBriefingSnapshotStore.ts",
  "gtmProductAccountMapStore.ts",
  "gtmWeeklyReviewStore.ts",
  "kanzleiMonthlyReportBaseline.ts",
  "leadOpsState.ts",
  "leadPersistence.ts",
  "leadSyncStore.ts",
];

for (const dependency of ["@aws-sdk/client-s3", "pg"]) {
  const version = packageJson.dependencies?.[dependency];
  if (!version) {
    errors.push(`package.json: ${dependency} must be a pinned runtime dependency`);
  } else if (!/^\d+\.\d+\.\d+$/.test(version)) {
    errors.push(`package.json: ${dependency} must use an exact version`);
  }
}

for (const invariant of [
  "COMPLIANCEHUB_RUNTIME_STORAGE_BACKEND must be s3 in production",
  "withS3RuntimeStorageLock",
  "S3Client",
  "COMPLIANCEHUB_S3_ACCESS_KEY_FILE",
  "COMPLIANCEHUB_S3_SECRET_ACCESS_KEY_FILE",
  "pg_advisory_xact_lock",
]) {
  if (!runtimeBoundary.includes(invariant)) {
    errors.push(`runtimeFileIO.ts: missing required invariant ${invariant}`);
  }
}

for (const invariant of [
  "tenant RLS/self-elevation guard",
  "cross-tenant reminder INSERT unexpectedly succeeded",
  "direct deletion audit INSERT unexpectedly succeeded",
  "runtime application roles must not own protected tables",
]) {
  if (!postgresContractTest.includes(invariant)) {
    errors.push(`PostgreSQL contract test: missing required invariant ${invariant}`);
  }
}

for (const invariant of [
  "COMPLIANCEHUB_RELATIONAL_RUNTIME_BACKEND must be postgres in production",
  "COMPLIANCEHUB_POSTGRES_ALLOWED_HOSTS",
  "POSTGRES_PASSWORD_FILE",
  "rejectUnauthorized: true",
  "PostgreSQL administrator identities are forbidden for application runtime",
  "withTenantRuntimePostgres",
  "withPlatformRuntimePostgres",
  "SET LOCAL statement_timeout",
  "SET LOCAL lock_timeout",
]) {
  if (!postgresBoundary.includes(invariant)) {
    errors.push(`runtimePostgres.ts: missing required invariant ${invariant}`);
  }
}

for (const invariant of [
  "advisor_mandant_history",
  "advisor_mandant_reminders",
  "row_version",
  "COMPLIANCEHUB_ADVISOR_RUNTIME_RETENTION_DAYS",
  "retention_until",
  "pg_advisory_xact_lock",
]) {
  if (!advisorPostgresStore.includes(invariant)) {
    errors.push(`advisorRuntimePostgresStore.ts: missing required invariant ${invariant}`);
  }
}

for (const invariant of [
  "FORCE ROW LEVEL SECURITY",
  "NOBYPASSRLS",
  "compliancehub_runtime_platform_app",
  "pg_has_role",
  "runtime_state_deletion_audit",
  "compliancehub.deletion_reason",
  "REVOKE ALL ON SCHEMA compliancehub_private FROM PUBLIC",
]) {
  if (!postgresMigration.includes(invariant)) {
    errors.push(`PostgreSQL migration: missing required invariant ${invariant}`);
  }
}

for (const store of ["advisorMandantHistoryStore.ts", "advisorMandantReminderStore.ts"]) {
  const source = readFileSync(resolve("src/lib", store), "utf8");
  if (!source.includes('from "@/lib/advisorRuntimePostgresStore"')) {
    errors.push(`${store}: must use the governed PostgreSQL advisor boundary`);
  }
  if (!source.includes("resolveRelationalRuntimeBackend")) {
    errors.push(`${store}: must fail closed through the relational runtime backend policy`);
  }
}

for (const forbidden of [
  "StorageSharedKeyCredential",
  "fromConnectionString",
  "AZURE_STORAGE_CONNECTION_STRING",
  "AZURE_STORAGE_ACCOUNT_KEY",
  "AZURE_POSTGRES_PASSWORD",
  "POSTGRES_PASSWORD=",
  "AWS_ACCESS_KEY_ID",
  "AWS_SECRET_ACCESS_KEY",
  "connectionString:",
]) {
  if (runtimeBoundary.includes(forbidden) || postgresBoundary.includes(forbidden)) {
    errors.push(`Runtime boundary: long-lived credential path ${forbidden} is forbidden`);
  }
}

for (const forbiddenVendorPath of ["@vercel/oidc", "getVercelOidcToken", 'env.VERCEL']) {
  if (runtimeBoundary.includes(forbiddenVendorPath)) {
    errors.push(`Runtime boundary: forbidden Vercel path ${forbiddenVendorPath}`);
  }
}

for (const forbiddenAzureStoragePath of [
  "@azure/storage-blob",
  "AZURE_STORAGE_",
  "azure_blob",
]) {
  if (runtimeBoundary.includes(forbiddenAzureStoragePath)) {
    errors.push(`Runtime boundary: removed Azure storage path ${forbiddenAzureStoragePath}`);
  }
}

for (const store of stores) {
  const path = resolve("src/lib", store);
  const source = readFileSync(path, "utf8");
  if (!source.includes('from "@/lib/runtimeFileIO"')) {
    errors.push(`${store}: must use the governed runtime storage boundary`);
  }
  if (/from ["']node:fs(?:\/promises)?["']/.test(source)) {
    errors.push(`${store}: direct filesystem access is forbidden`);
  }
}

if (errors.length) {
  process.stderr.write(`Runtime storage verification failed:\n- ${errors.join("\n- ")}\n`);
  process.exit(1);
}

process.stdout.write("Runtime storage verification passed\n");
