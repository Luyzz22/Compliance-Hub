import { readFileSync, readdirSync, statSync } from "node:fs";
import { extname, join, resolve } from "node:path";

const production =
  process.env.VERCEL_ENV === "production" ||
  process.env.COMPLIANCEHUB_RELEASE_CHANNEL === "production";

if (!production) {
  process.stdout.write("Enterprise release gate: local/non-production build\n");
  process.exit(0);
}

const errors = [];
const releaseProfile = process.env.COMPLIANCEHUB_RELEASE_PROFILE?.trim() || "";
const supportedReleaseProfiles = new Set(["public_site", "enterprise"]);
const guidPattern =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const nilGuid = "00000000-0000-0000-0000-000000000000";

const legalRequired = [
  "COMPLIANCEHUB_APP_ORIGIN",
  "COMPLIANCEHUB_TRUSTED_HOSTS",
  "COMPLIANCEHUB_LEGAL_ENTITY_NAME",
  "COMPLIANCEHUB_LEGAL_REPRESENTATIVE",
  "COMPLIANCEHUB_LEGAL_STREET",
  "COMPLIANCEHUB_LEGAL_POSTAL_CODE",
  "COMPLIANCEHUB_LEGAL_CITY",
  "COMPLIANCEHUB_LEGAL_COUNTRY",
  "COMPLIANCEHUB_LEGAL_EMAIL",
  "COMPLIANCEHUB_LEGAL_REGISTER_COURT",
  "COMPLIANCEHUB_LEGAL_REGISTER_NUMBER",
  "COMPLIANCEHUB_LEGAL_VAT_ID",
  "COMPLIANCEHUB_PRIVACY_EMAIL",
  "COMPLIANCEHUB_PRIVACY_NOTICE_VERSION",
  "COMPLIANCEHUB_PRIVACY_REVIEWED_AT",
  "COMPLIANCEHUB_PRIVACY_LOG_RETENTION_DAYS",
  "COMPLIANCEHUB_PRIVACY_LEAD_RETENTION_DAYS",
  "COMPLIANCEHUB_SECURITY_CONTACT",
];

function requireKeys(keys) {
  for (const key of keys) {
    if (!process.env[key]?.trim()) errors.push(`${key} is required`);
  }
}

function validateRetentionDays(key, minimum, maximum) {
  const value = Number(process.env[key]);
  if (!Number.isSafeInteger(value) || value < minimum || value > maximum) {
    errors.push(`${key} must be an approved value between ${minimum} and ${maximum}`);
  }
}

if (!supportedReleaseProfiles.has(releaseProfile)) {
  errors.push(
    "COMPLIANCEHUB_RELEASE_PROFILE must be public_site or enterprise in production",
  );
}

requireKeys(legalRequired);

if (process.env.COMPLIANCEHUB_LEGAL_PUBLISH_READY !== "true") {
  errors.push(
    "COMPLIANCEHUB_LEGAL_PUBLISH_READY must be true after documented legal review",
  );
}

let appOrigin;
try {
  appOrigin = new URL(process.env.COMPLIANCEHUB_APP_ORIGIN || "");
  if (
    appOrigin.protocol !== "https:" ||
    appOrigin.username ||
    appOrigin.password ||
    appOrigin.pathname !== "/" ||
    appOrigin.search ||
    appOrigin.hash
  ) {
    errors.push("COMPLIANCEHUB_APP_ORIGIN must be a bare HTTPS origin");
  }
} catch {
  errors.push("COMPLIANCEHUB_APP_ORIGIN must be a valid HTTPS origin");
}

const trustedHosts = new Set(
  (process.env.COMPLIANCEHUB_TRUSTED_HOSTS || "")
    .split(",")
    .map((host) => host.trim().toLowerCase())
    .filter(Boolean),
);
if (appOrigin && !trustedHosts.has(appOrigin.host.toLowerCase())) {
  errors.push("COMPLIANCEHUB_TRUSTED_HOSTS must include the application host");
}

const reviewedAt = process.env.COMPLIANCEHUB_PRIVACY_REVIEWED_AT || "";
const reviewedDate = /^\d{4}-\d{2}-\d{2}$/.test(reviewedAt)
  ? new Date(`${reviewedAt}T00:00:00.000Z`)
  : new Date(Number.NaN);
const legalReviewMaximumAgeMs = 366 * 24 * 60 * 60 * 1_000;
if (Number.isNaN(reviewedDate.getTime())) {
  errors.push("COMPLIANCEHUB_PRIVACY_REVIEWED_AT must use YYYY-MM-DD");
} else if (reviewedDate.getTime() > Date.now()) {
  errors.push("COMPLIANCEHUB_PRIVACY_REVIEWED_AT cannot be in the future");
} else if (Date.now() - reviewedDate.getTime() > legalReviewMaximumAgeMs) {
  errors.push("The privacy notice review must be renewed at least annually");
}

validateRetentionDays("COMPLIANCEHUB_PRIVACY_LOG_RETENTION_DAYS", 1, 365);
validateRetentionDays("COMPLIANCEHUB_PRIVACY_LEAD_RETENTION_DAYS", 1, 3_650);

if (process.env.NEXT_PUBLIC_API_KEY) {
  errors.push("NEXT_PUBLIC_API_KEY is forbidden because it exposes a bearer credential");
}
if (process.env.COMPLIANCEHUB_ALLOW_GLOBAL_API_KEYS === "true") {
  errors.push("Global cross-tenant API keys are forbidden in production");
}
if ((process.env.COMPLIANCEHUB_LLM_PII_MODE || "block") !== "block") {
  errors.push("COMPLIANCEHUB_LLM_PII_MODE must be block in production");
}

if (releaseProfile === "public_site") {
  if (appOrigin?.origin !== "https://complywithai.de") {
    errors.push(
      "The public_site application origin must be https://complywithai.de",
    );
  }
  if (process.env.COMPLIANCEHUB_PUBLIC_SITE_READY !== "true") {
    errors.push(
      "COMPLIANCEHUB_PUBLIC_SITE_READY must attest the reviewed stateless public release",
    );
  }
  for (const key of [
    "COMPLIANCEHUB_PUBLIC_DEMO_ENABLED",
    "COMPLIANCEHUB_PUBLIC_LEAD_CAPTURE_ENABLED",
    "COMPLIANCEHUB_ENTRA_ENABLED",
    "COMPLIANCEHUB_CSP_REPORTING_READY",
  ]) {
    if (process.env[key] === "true") {
      errors.push(`${key} must remain disabled in the public_site release`);
    }
  }

  const allowedComplianceHubKeys = new Set([
    ...legalRequired,
    "COMPLIANCEHUB_RELEASE_CHANNEL",
    "COMPLIANCEHUB_RELEASE_PROFILE",
    "COMPLIANCEHUB_PUBLIC_SITE_READY",
    "COMPLIANCEHUB_PUBLIC_DEMO_ENABLED",
    "COMPLIANCEHUB_PUBLIC_LEAD_CAPTURE_ENABLED",
    "COMPLIANCEHUB_ENTRA_ENABLED",
    "COMPLIANCEHUB_CSP_REPORTING_READY",
    "COMPLIANCEHUB_LEGAL_PHONE",
    "COMPLIANCEHUB_LEGAL_PUBLISH_READY",
    "COMPLIANCEHUB_PRIVACY_DPO_CONTACT",
    "COMPLIANCEHUB_LLM_PII_MODE",
  ]);
  const forbiddenPublicPrefixes = [
    "POSTGRES_",
    "SUPABASE_",
    "AZURE_",
  ];
  const forbiddenPublicExact = new Set(["DATABASE_URL", "PGPASSWORD"]);

  for (const [key, rawValue] of Object.entries(process.env)) {
    if (!rawValue?.trim()) continue;
    const unapprovedComplianceHubKey =
      key.startsWith("COMPLIANCEHUB_") && !allowedComplianceHubKeys.has(key);
    const unapprovedBrowserKey =
      key.startsWith("NEXT_PUBLIC_") && !key.startsWith("NEXT_PUBLIC_VERCEL_");
    const forbiddenInfrastructureKey =
      forbiddenPublicExact.has(key) ||
      forbiddenPublicPrefixes.some((prefix) => key.startsWith(prefix));
    if (
      unapprovedComplianceHubKey ||
      unapprovedBrowserKey ||
      forbiddenInfrastructureKey
    ) {
      errors.push(`${key} is forbidden in the stateless public_site release`);
    }
  }
}

if (releaseProfile === "enterprise") {
  const enterpriseRequired = [
    "COMPLIANCEHUB_API_BASE_URL",
    "COMPLIANCEHUB_API_KEY",
    "COMPLIANCEHUB_BFF_SHARED_SECRET",
    "COMPLIANCEHUB_AUDIT_PSEUDONYMIZATION_KEY",
    "COMPLIANCEHUB_ENTRA_TENANT_ID",
    "COMPLIANCEHUB_ENTRA_CLIENT_ID",
    "COMPLIANCEHUB_ENTRA_CLIENT_SECRET",
    "COMPLIANCEHUB_ENTRA_PROVIDER_ID",
    "COMPLIANCEHUB_AUTH_TRANSACTION_SECRET",
    "COMPLIANCEHUB_RUNTIME_STORAGE_BACKEND",
    "COMPLIANCEHUB_RUNTIME_STORAGE_AUTH",
    "AZURE_STORAGE_ACCOUNT_NAME",
    "AZURE_STORAGE_CONTAINER_NAME",
    "COMPLIANCEHUB_RELATIONAL_RUNTIME_BACKEND",
    "AZURE_POSTGRES_HOST",
    "AZURE_POSTGRES_DATABASE",
    "AZURE_POSTGRES_USER",
    "COMPLIANCEHUB_ADVISOR_RUNTIME_RETENTION_DAYS",
  ];
  requireKeys(enterpriseRequired);

  for (const key of [
    "COMPLIANCEHUB_ENTRA_TENANT_ID",
    "COMPLIANCEHUB_ENTRA_CLIENT_ID",
    "COMPLIANCEHUB_ENTRA_PROVIDER_ID",
  ]) {
    const value = process.env[key]?.trim().toLowerCase() || "";
    if (value && (!guidPattern.test(value) || value === nilGuid)) {
      errors.push(`${key} must be a non-placeholder GUID`);
    }
  }

  const requiredAttestations = {
    COMPLIANCEHUB_ENTERPRISE_AUTH_READY:
      "the reviewed authentication boundary",
    COMPLIANCEHUB_ENTRA_CONDITIONAL_ACCESS_READY:
      "Entra MFA and Conditional Access evidence",
    COMPLIANCEHUB_ENTRA_PROVISIONING_READY:
      "Entra provisioning and access recertification evidence",
    COMPLIANCEHUB_RUNTIME_STORAGE_READY:
      "Azure storage region, RBAC, network, diagnostics and restore evidence",
    COMPLIANCEHUB_CSP_REPORTING_READY:
      "CSP reporting privacy, SIEM retention, alerting and abuse controls",
    COMPLIANCEHUB_RELATIONAL_RUNTIME_READY:
      "Azure PostgreSQL region, Entra role, TLS, schema and connection evidence",
    COMPLIANCEHUB_POSTGRES_RLS_READY:
      "PostgreSQL FORCE RLS and cross-tenant denial evidence",
    COMPLIANCEHUB_POSTGRES_NETWORK_READY:
      "Azure PostgreSQL private network and firewall evidence",
    COMPLIANCEHUB_POSTGRES_BACKUP_RESTORE_READY:
      "Azure PostgreSQL PITR and restore-test evidence",
    COMPLIANCEHUB_POSTGRES_RETENTION_READY:
      "PostgreSQL retention, legal-hold and deletion-audit evidence",
    COMPLIANCEHUB_POSTGRES_DATA_MIGRATION_READY:
      "PostgreSQL migration counts, checksums and rollback evidence",
    COMPLIANCEHUB_POSTGRES_SUPPLY_CHAIN_READY:
      "PostgreSQL client dependency and supply-chain evidence",
  };
  for (const [key, evidence] of Object.entries(requiredAttestations)) {
    if (process.env[key] !== "true") {
      errors.push(`${key} must attest ${evidence}`);
    }
  }

  if (process.env.COMPLIANCEHUB_ENTRA_ENABLED !== "true") {
    errors.push("COMPLIANCEHUB_ENTRA_ENABLED must be true for production identity");
  }
  if (process.env.COMPLIANCEHUB_RUNTIME_STORAGE_BACKEND !== "azure_blob") {
    errors.push("COMPLIANCEHUB_RUNTIME_STORAGE_BACKEND must be azure_blob in production");
  }
  if (process.env.COMPLIANCEHUB_RELATIONAL_RUNTIME_BACKEND !== "azure_postgres") {
    errors.push(
      "COMPLIANCEHUB_RELATIONAL_RUNTIME_BACKEND must be azure_postgres in production",
    );
  }

  validateRetentionDays("COMPLIANCEHUB_ADVISOR_RUNTIME_RETENTION_DAYS", 30, 3_650);

  const postgresHost = process.env.AZURE_POSTGRES_HOST?.trim().toLowerCase() || "";
  if (
    !/^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.postgres\.database\.azure\.com$/.test(
      postgresHost,
    )
  ) {
    errors.push("AZURE_POSTGRES_HOST must be an Azure PostgreSQL hostname");
  }
  if (
    ["postgres", "azure_pg_admin", "azuresu"].includes(
      process.env.AZURE_POSTGRES_USER?.trim().toLowerCase() || "",
    )
  ) {
    errors.push(
      "Azure PostgreSQL administrator identities are forbidden for application runtime",
    );
  }

  for (const forbiddenCredential of [
    "AZURE_POSTGRES_PASSWORD",
    "PGPASSWORD",
    "POSTGRES_URL",
    "DATABASE_URL",
  ]) {
    if (process.env[forbiddenCredential]?.trim()) {
      errors.push(
        `${forbiddenCredential} is forbidden; use short-lived Microsoft Entra tokens`,
      );
    }
  }

  const runtimeStorageAuth = process.env.COMPLIANCEHUB_RUNTIME_STORAGE_AUTH;
  if (runtimeStorageAuth !== "managed_identity" && runtimeStorageAuth !== "vercel_oidc") {
    errors.push("Runtime storage must use managed_identity or vercel_oidc authentication");
  }
  if (process.env.VERCEL && runtimeStorageAuth !== "vercel_oidc") {
    errors.push("Vercel production runtime storage must use OIDC federation");
  }
  if (runtimeStorageAuth === "vercel_oidc") {
    requireKeys(["AZURE_TENANT_ID", "AZURE_CLIENT_ID"]);
  }

  for (const [key, minimumLength] of [
    ["COMPLIANCEHUB_AUDIT_PSEUDONYMIZATION_KEY", 32],
    ["COMPLIANCEHUB_BFF_SHARED_SECRET", 32],
    ["COMPLIANCEHUB_ENTRA_CLIENT_SECRET", 32],
    ["COMPLIANCEHUB_AUTH_TRANSACTION_SECRET", 32],
  ]) {
    if ((process.env[key] || "").length < minimumLength) {
      errors.push(`${key} must contain at least ${minimumLength} characters`);
    }
  }

  if (process.env.COMPLIANCEHUB_LLM_PREFER_AZURE === "true") {
    requireKeys(["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT"]);
    if (process.env.AZURE_OPENAI_AUTH !== "managed_identity") {
      errors.push("AZURE_OPENAI_AUTH must be managed_identity in production");
    }
    if (process.env.COMPLIANCEHUB_LLM_ASSUME_AZURE_EU !== "true") {
      errors.push("Azure EU regional/Data Zone processing must be reviewed and attested");
    }
  }
}

const publicCredentialPattern = /NEXT_PUBLIC_(?:API_KEY|SECRET|TOKEN)/;
const sourceRoot = resolve("src");
const sourceExtensions = new Set([".js", ".jsx", ".mjs", ".ts", ".tsx"]);

function scanPublicCredentials(directory) {
  for (const entry of readdirSync(directory)) {
    const path = join(directory, entry);
    const metadata = statSync(path);
    if (metadata.isDirectory()) {
      scanPublicCredentials(path);
    } else if (sourceExtensions.has(extname(path))) {
      const content = readFileSync(path, "utf8");
      if (publicCredentialPattern.test(content)) {
        errors.push(`${path}: public credential environment variables are forbidden`);
      }
    }
  }
}

scanPublicCredentials(sourceRoot);

if (errors.length) {
  process.stderr.write(
    `Enterprise release gate failed (${releaseProfile || "missing profile"}):\n- ${errors.join("\n- ")}\n`,
  );
  process.exit(1);
}

process.stdout.write(`Enterprise release gate passed (${releaseProfile})\n`);
