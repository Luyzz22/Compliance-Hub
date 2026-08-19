import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { extname, join, resolve } from "node:path";

const production = process.env.COMPLIANCEHUB_RELEASE_CHANNEL === "production";

if (process.env.VERCEL || process.env.VERCEL_ENV) {
  process.stderr.write(
    "Enterprise release gate failed: Vercel runtime variables are forbidden in the Hetzner-first profile\n",
  );
  process.exit(1);
}

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

function rejectPlaceholders(keys) {
  const placeholderPattern = /(?:replace-after|replace-with|change-?me|todo|tbd|your-)/i;
  for (const key of keys) {
    const value = process.env[key]?.trim() || "";
    if (value && (placeholderPattern.test(value) || /[\r\n]/.test(value))) {
      errors.push(`${key} must contain a reviewed production value, not a placeholder`);
    }
  }
}

function environmentFlagIsTrue(key) {
  return ["1", "true", "yes", "on"].includes(
    process.env[key]?.trim().toLowerCase() || "",
  );
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
rejectPlaceholders(legalRequired);

for (const emailKey of ["COMPLIANCEHUB_LEGAL_EMAIL", "COMPLIANCEHUB_PRIVACY_EMAIL"]) {
  const value = process.env[emailKey]?.trim() || "";
  if (value && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value)) {
    errors.push(`${emailKey} must be a valid email address`);
  }
}
if (
  process.env.COMPLIANCEHUB_LEGAL_COUNTRY === "Deutschland" &&
  process.env.COMPLIANCEHUB_LEGAL_POSTAL_CODE &&
  !/^\d{5}$/.test(process.env.COMPLIANCEHUB_LEGAL_POSTAL_CODE)
) {
  errors.push("COMPLIANCEHUB_LEGAL_POSTAL_CODE must be a five-digit German postal code");
}
if (
  process.env.COMPLIANCEHUB_LEGAL_COUNTRY === "Deutschland" &&
  process.env.COMPLIANCEHUB_LEGAL_VAT_ID &&
  !/^DE\d{9}$/.test(process.env.COMPLIANCEHUB_LEGAL_VAT_ID)
) {
  errors.push("COMPLIANCEHUB_LEGAL_VAT_ID must use the German DE plus nine-digit format");
}
const securityContact = process.env.COMPLIANCEHUB_SECURITY_CONTACT?.trim() || "";
if (securityContact) {
  try {
    const contactUrl = new URL(securityContact);
    if (!(["https:", "mailto:"].includes(contactUrl.protocol)) || contactUrl.username || contactUrl.password) {
      errors.push("COMPLIANCEHUB_SECURITY_CONTACT must be an HTTPS or mailto contact");
    }
  } catch {
    errors.push("COMPLIANCEHUB_SECURITY_CONTACT must be an HTTPS or mailto contact");
  }
}

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
    // Vom Laufzeit-Image gesetzt: im Runtime-Layer existiert `src` nicht mehr,
    // die Quellcode-Prüfung greift dort bewusst nicht. Kein Konfigurationswert.
    "COMPLIANCEHUB_RUNTIME_PREFLIGHT",
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
    const unapprovedBrowserKey = key.startsWith("NEXT_PUBLIC_");
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
    "COMPLIANCEHUB_API_ALLOWED_HOSTS",
    "COMPLIANCEHUB_SOVEREIGNTY_MODE",
    "COMPLIANCEHUB_BFF_SHARED_SECRET_FILE",
    "COMPLIANCEHUB_ENTRA_TENANT_ID",
    "COMPLIANCEHUB_ENTRA_CLIENT_ID",
    "COMPLIANCEHUB_ENTRA_CLIENT_SECRET_FILE",
    "COMPLIANCEHUB_ENTRA_PROVIDER_ID",
    "COMPLIANCEHUB_AUTH_TRANSACTION_SECRET_FILE",
    "LEAD_ADMIN_SECRET_FILE",
    "COMPLIANCEHUB_RUNTIME_STORAGE_BACKEND",
    "COMPLIANCEHUB_S3_ENDPOINT",
    "COMPLIANCEHUB_S3_REGION",
    "COMPLIANCEHUB_S3_BUCKET",
    "COMPLIANCEHUB_S3_ACCESS_KEY_FILE",
    "COMPLIANCEHUB_S3_SECRET_ACCESS_KEY_FILE",
    "COMPLIANCEHUB_RELATIONAL_RUNTIME_BACKEND",
    "COMPLIANCEHUB_POSTGRES_ALLOWED_HOSTS",
    "POSTGRES_HOST",
    "POSTGRES_DATABASE",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD_FILE",
    "COMPLIANCEHUB_ADVISOR_RUNTIME_RETENTION_DAYS",
    "COMPLIANCEHUB_SESSION_TTL_MINUTES",
  ];
  requireKeys(enterpriseRequired);
  rejectPlaceholders([
    ...enterpriseRequired,
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_DEPLOYMENT",
  ]);
  if (process.env.NEXT_PUBLIC_API_BASE_URL?.trim()) {
    errors.push(
      "NEXT_PUBLIC_API_BASE_URL is forbidden; authenticated browser traffic must use the same-origin BFF",
    );
  }

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
      "S3 location, private bucket, credential rotation, diagnostics and restore evidence",
    COMPLIANCEHUB_CSP_REPORTING_READY:
      "CSP reporting privacy, SIEM retention, alerting and abuse controls",
    COMPLIANCEHUB_RELATIONAL_RUNTIME_READY:
      "Hetzner PostgreSQL location, runtime role, TLS, schema and connection evidence",
    COMPLIANCEHUB_POSTGRES_RLS_READY:
      "PostgreSQL FORCE RLS and cross-tenant denial evidence",
    COMPLIANCEHUB_POSTGRES_NETWORK_READY:
      "PostgreSQL private network and firewall evidence",
    COMPLIANCEHUB_POSTGRES_BACKUP_RESTORE_READY:
      "Hetzner PostgreSQL PITR and restore-test evidence",
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
  for (const localIdentityFlag of [
    "COMPLIANCEHUB_PASSWORD_LOGIN_ENABLED",
    "COMPLIANCEHUB_SELF_REGISTRATION_ENABLED",
  ]) {
    if (environmentFlagIsTrue(localIdentityFlag)) {
      errors.push(`${localIdentityFlag} must remain disabled in enterprise production`);
    }
  }
  if (
    !["standard_dach", "eu_sovereign", "strict_sovereign"].includes(
      process.env.COMPLIANCEHUB_SOVEREIGNTY_MODE || "",
    )
  ) {
    errors.push("COMPLIANCEHUB_SOVEREIGNTY_MODE must select a restrictive production mode");
  }
  if (process.env.COMPLIANCEHUB_RUNTIME_STORAGE_BACKEND !== "s3") {
    errors.push("COMPLIANCEHUB_RUNTIME_STORAGE_BACKEND must be s3 in production");
  }
  if (process.env.COMPLIANCEHUB_RELATIONAL_RUNTIME_BACKEND !== "postgres") {
    errors.push(
      "COMPLIANCEHUB_RELATIONAL_RUNTIME_BACKEND must be postgres in production",
    );
  }

  validateRetentionDays("COMPLIANCEHUB_ADVISOR_RUNTIME_RETENTION_DAYS", 30, 3_650);
  validateRetentionDays("COMPLIANCEHUB_SESSION_TTL_MINUTES", 5, 480);

  const postgresHost = process.env.POSTGRES_HOST?.trim().toLowerCase() || "";
  const allowedPostgresHosts = new Set(
    (process.env.COMPLIANCEHUB_POSTGRES_ALLOWED_HOSTS || "")
      .split(",")
      .map((host) => host.trim().toLowerCase())
      .filter(Boolean),
  );
  if (!allowedPostgresHosts.has(postgresHost)) {
    errors.push("POSTGRES_HOST must be listed in COMPLIANCEHUB_POSTGRES_ALLOWED_HOSTS");
  }
  if (
    ["postgres", "azure_pg_admin", "azuresu", "root"].includes(
      process.env.POSTGRES_USER?.trim().toLowerCase() || "",
    )
  ) {
    errors.push(
      "PostgreSQL administrator identities are forbidden for application runtime",
    );
  }

  for (const forbiddenCredential of [
    "AZURE_POSTGRES_PASSWORD",
    "PGPASSWORD",
    "POSTGRES_URL",
    "DATABASE_URL",
    "POSTGRES_PASSWORD",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AZURE_OPENAI_API_KEY",
    "COMPLIANCEHUB_API_KEY",
    "COMPLIANCEHUB_BFF_SHARED_SECRET",
    "COMPLIANCEHUB_AUDIT_PSEUDONYMIZATION_KEY",
    "COMPLIANCEHUB_ENTRA_CLIENT_SECRET",
    "COMPLIANCEHUB_AUTH_TRANSACTION_SECRET",
    "LEAD_ADMIN_SECRET",
    "GTM_ALERT_SECRET",
    "LEAD_SYNC_N8N_SECRET",
    "LEAD_INBOUND_WEBHOOK_SECRET",
    "GTM_ALERT_WEBHOOK_SECRET",
    "COMPLIANCEHUB_N8N_WEBHOOK_SECRET",
    "COMPLIANCEHUB_EXPORT_WEBHOOK_SECRET",
    "INTERNAL_HEALTH_API_KEY",
  ]) {
    if (process.env[forbiddenCredential]?.trim()) {
      errors.push(
        `${forbiddenCredential} is forbidden; mount a rotated OpenBao-managed secret file`,
      );
    }
  }

  for (const forbiddenProviderVariable of [
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "CLAUDE_API_KEY",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_API_URL",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "LANGSMITH_API_KEY",
    "LANGSMITH_ENDPOINT",
    "LANGCHAIN_API_KEY",
    "LANGCHAIN_ENDPOINT",
    "POSTHOG_API_KEY",
    "POSTHOG_HOST",
    "TEMPORAL_API_KEY",
  ]) {
    if (process.env[forbiddenProviderVariable]?.trim()) {
      errors.push(
        `${forbiddenProviderVariable} is forbidden; Azure is the only approved external AI/provider exception`,
      );
    }
  }
  if (environmentFlagIsTrue("COMPLIANCEHUB_TEMPORAL_ENABLED")) {
    const address = process.env.TEMPORAL_ADDRESS?.trim() || "";
    const allowedHosts = new Set(
      (process.env.COMPLIANCEHUB_TEMPORAL_ALLOWED_HOSTS || "")
        .split(",")
        .map((host) => host.trim().toLowerCase())
        .filter(Boolean),
    );
    const match = address.match(/^\[?([^\]]+)\]?:([1-9]\d{0,4})$/);
    const hostname = match?.[1]?.toLowerCase() || "";
    const managedTemporalHost =
      hostname === "temporal.io" ||
      hostname.endsWith(".temporal.io") ||
      hostname.endsWith(".tmprl.cloud");
    if (!match || managedTemporalHost || !allowedHosts.has(hostname)) {
      errors.push(
        "Enabled Temporal must use an exact allowlisted self-hosted host:port endpoint",
      );
    }
  }
  for (const forbiddenProviderFlag of [
    "COMPLIANCEHUB_LLM_US_CLOUD_OK",
    "COMPLIANCEHUB_LLM_ASSUME_CLAUDE_EU",
    "LANGCHAIN_TRACING_V2",
    "LANGSMITH_TRACING",
  ]) {
    if (environmentFlagIsTrue(forbiddenProviderFlag)) {
      errors.push(
        `${forbiddenProviderFlag} is forbidden; Azure is the only approved external AI/provider exception`,
      );
    }
  }
  if (
    process.env.HAYSTACK_TELEMETRY_ENABLED &&
    !["0", "false", "no", "off"].includes(
      process.env.HAYSTACK_TELEMETRY_ENABLED.trim().toLowerCase(),
    )
  ) {
    errors.push("HAYSTACK_TELEMETRY_ENABLED must be false in production");
  }

  for (const key of [
    "COMPLIANCEHUB_S3_ACCESS_KEY_FILE",
    "COMPLIANCEHUB_S3_SECRET_ACCESS_KEY_FILE",
    "POSTGRES_PASSWORD_FILE",
    "COMPLIANCEHUB_BFF_SHARED_SECRET_FILE",
    "COMPLIANCEHUB_ENTRA_CLIENT_SECRET_FILE",
    "COMPLIANCEHUB_AUTH_TRANSACTION_SECRET_FILE",
    "LEAD_ADMIN_SECRET_FILE",
    "GTM_ALERT_SECRET_FILE",
    "LEAD_SYNC_N8N_SECRET_FILE",
    "LEAD_INBOUND_WEBHOOK_SECRET_FILE",
    "GTM_ALERT_WEBHOOK_SECRET_FILE",
    "COMPLIANCEHUB_N8N_WEBHOOK_SECRET_FILE",
    "COMPLIANCEHUB_EXPORT_WEBHOOK_SECRET_FILE",
    "INTERNAL_HEALTH_API_KEY_FILE",
  ]) {
    if (process.env[key] && !process.env[key].startsWith("/")) {
      errors.push(`${key} must be an absolute mounted secret-file path`);
    }
  }

  for (const [key, rawValue] of Object.entries(process.env)) {
    if (
      rawValue?.trim() &&
      (key.startsWith("HUBSPOT_") ||
        key.startsWith("PIPEDRIVE_") ||
        key.startsWith("STRIPE_") ||
        key.startsWith("COMPLIANCEHUB_STRIPE_"))
    ) {
      errors.push(`${key} is forbidden by the sovereign production provider policy`);
    }
  }
  for (const key of ["LEAD_SYNC_HUBSPOT_STUB", "LEAD_SYNC_PIPEDRIVE_STUB"]) {
    if (process.env[key] === "1") {
      errors.push(`${key} is forbidden in production`);
    }
  }

  const allowedWebhookHosts = new Set(
    (process.env.COMPLIANCEHUB_OUTBOUND_WEBHOOK_ALLOWED_HOSTS || "")
      .split(",")
      .map((host) => host.trim().toLowerCase())
      .filter(Boolean),
  );
  const forbiddenWebhookSuffixes = [
    "hubapi.com",
    "hubspot.com",
    "pipedrive.com",
    "vercel.app",
    "vercel.com",
    "neon.tech",
    "stripe.com",
    "posthog.com",
    "sentry.io",
  ];
  for (const [urlKey, secretFileKey] of [
    ["LEAD_SYNC_N8N_URL", "LEAD_SYNC_N8N_SECRET_FILE"],
    ["LEAD_INBOUND_WEBHOOK_URL", "LEAD_INBOUND_WEBHOOK_SECRET_FILE"],
    ["GTM_ALERT_WEBHOOK_URL", "GTM_ALERT_WEBHOOK_SECRET_FILE"],
  ]) {
    const rawUrl = process.env[urlKey]?.trim();
    if (!rawUrl) continue;
    requireKeys([secretFileKey, "COMPLIANCEHUB_OUTBOUND_WEBHOOK_ALLOWED_HOSTS"]);
    try {
      const endpoint = new URL(rawUrl);
      const hostname = endpoint.hostname.toLowerCase();
      const forbiddenHost = forbiddenWebhookSuffixes.some(
        (suffix) => hostname === suffix || hostname.endsWith(`.${suffix}`),
      );
      if (
        endpoint.protocol !== "https:" ||
        endpoint.username ||
        endpoint.password ||
        endpoint.search ||
        endpoint.hash ||
        forbiddenHost ||
        !allowedWebhookHosts.has(hostname)
      ) {
        errors.push(`${urlKey} must be an approved allowlisted HTTPS endpoint`);
      }
    } catch {
      errors.push(`${urlKey} must be a valid absolute URL`);
    }
  }
  try {
    const endpoint = new URL(process.env.COMPLIANCEHUB_S3_ENDPOINT || "");
    if (
      endpoint.protocol !== "https:" ||
      !["fsn1.your-objectstorage.com", "nbg1.your-objectstorage.com"]
        .concat(
          (process.env.COMPLIANCEHUB_S3_ALLOWED_HOSTS || "")
            .split(",")
            .map((host) => host.trim().toLowerCase())
            .filter(Boolean),
        )
        .includes(endpoint.hostname.toLowerCase())
    ) {
      errors.push("COMPLIANCEHUB_S3_ENDPOINT must be an approved HTTPS endpoint");
    }
  } catch {
    errors.push("COMPLIANCEHUB_S3_ENDPOINT must be a valid HTTPS endpoint");
  }

  if (process.env.COMPLIANCEHUB_LLM_PREFER_AZURE === "true") {
    requireKeys(["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT"]);
    if (process.env.AZURE_OPENAI_AUTH !== "client_certificate") {
      errors.push("Hetzner production requires certificate-backed Azure OpenAI identity");
    } else {
      requireKeys([
        "AZURE_TENANT_ID",
        "AZURE_CLIENT_ID",
        "AZURE_CLIENT_CERTIFICATE_PATH",
      ]);
      if (
        process.env.AZURE_CLIENT_CERTIFICATE_PATH &&
        !process.env.AZURE_CLIENT_CERTIFICATE_PATH.startsWith("/")
      ) {
        errors.push("AZURE_CLIENT_CERTIFICATE_PATH must be an absolute mounted secret path");
      }
    }
    if (process.env.COMPLIANCEHUB_LLM_ASSUME_AZURE_EU !== "true") {
      errors.push("Azure EU regional/Data Zone processing must be reviewed and attested");
    }
    if (process.env.COMPLIANCEHUB_SOVEREIGNTY_MODE !== "standard_dach") {
      errors.push("Azure OpenAI is permitted only in standard_dach mode");
    }
    try {
      const endpoint = new URL(process.env.AZURE_OPENAI_ENDPOINT || "");
      const approvedAzureHost = ["openai.azure.com", "services.ai.azure.com"].some(
        (suffix) =>
          endpoint.hostname.endsWith(`.${suffix}`) && endpoint.hostname !== suffix,
      );
      if (
        endpoint.protocol !== "https:" ||
        endpoint.username ||
        endpoint.password ||
        endpoint.search ||
        endpoint.hash ||
        !approvedAzureHost ||
        !["/", "/openai/v1"].includes(endpoint.pathname)
      ) {
        errors.push("AZURE_OPENAI_ENDPOINT must be an approved bare Azure HTTPS endpoint");
      }
    } catch {
      errors.push("AZURE_OPENAI_ENDPOINT must be a valid Azure HTTPS endpoint");
    }
  }
}

const publicCredentialPattern = /NEXT_PUBLIC_(?:API_KEY|SECRET|TOKEN)/;
const hardcodedLegacyCredentialPattern = /tenant-overview-key/;
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
      if (hardcodedLegacyCredentialPattern.test(content)) {
        errors.push(`${path}: hardcoded legacy API credentials are forbidden`);
      }
    }
  }
}

if (existsSync(sourceRoot)) {
  scanPublicCredentials(sourceRoot);
} else if (process.env.COMPLIANCEHUB_RUNTIME_PREFLIGHT !== "true") {
  errors.push("src is unavailable and COMPLIANCEHUB_RUNTIME_PREFLIGHT is not enabled");
}

if (errors.length) {
  process.stderr.write(
    `Enterprise release gate failed (${releaseProfile || "missing profile"}):\n- ${errors.join("\n- ")}\n`,
  );
  process.exit(1);
}

process.stdout.write(`Enterprise release gate passed (${releaseProfile})\n`);
