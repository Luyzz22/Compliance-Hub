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
const guidPattern =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const nilGuid = "00000000-0000-0000-0000-000000000000";
const required = [
  "COMPLIANCEHUB_API_BASE_URL",
  "COMPLIANCEHUB_API_KEY",
  "COMPLIANCEHUB_APP_ORIGIN",
  "COMPLIANCEHUB_BFF_SHARED_SECRET",
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
];

for (const key of required) {
  if (!process.env[key]?.trim()) errors.push(`${key} is required`);
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

if (process.env.COMPLIANCEHUB_LEGAL_PUBLISH_READY !== "true") {
  errors.push(
    "COMPLIANCEHUB_LEGAL_PUBLISH_READY must be true after legal review",
  );
}
if (process.env.COMPLIANCEHUB_ENTERPRISE_AUTH_READY !== "true") {
  errors.push(
    "COMPLIANCEHUB_ENTERPRISE_AUTH_READY must attest the reviewed auth boundary",
  );
}
if (process.env.COMPLIANCEHUB_ENTRA_ENABLED !== "true") {
  errors.push(
    "COMPLIANCEHUB_ENTRA_ENABLED must be true for production identity",
  );
}
if (process.env.COMPLIANCEHUB_ENTRA_CONDITIONAL_ACCESS_READY !== "true") {
  errors.push("Entra MFA and Conditional Access evidence must be approved");
}
if (process.env.COMPLIANCEHUB_ENTRA_PROVISIONING_READY !== "true") {
  errors.push(
    "Entra identity provisioning and access recertification must be approved",
  );
}
if (process.env.COMPLIANCEHUB_RUNTIME_STORAGE_READY !== "true") {
  errors.push(
    "Azure runtime storage region, RBAC, network, diagnostics and restore evidence must be approved",
  );
}
if (process.env.COMPLIANCEHUB_CSP_REPORTING_READY !== "true") {
  errors.push(
    "CSP reporting privacy, SIEM retention, alerting and abuse controls must be approved",
  );
}
if (process.env.COMPLIANCEHUB_RUNTIME_STORAGE_BACKEND !== "azure_blob") {
  errors.push("COMPLIANCEHUB_RUNTIME_STORAGE_BACKEND must be azure_blob in production");
}
const runtimeStorageAuth = process.env.COMPLIANCEHUB_RUNTIME_STORAGE_AUTH;
if (runtimeStorageAuth !== "managed_identity" && runtimeStorageAuth !== "vercel_oidc") {
  errors.push("Runtime storage must use managed_identity or vercel_oidc authentication");
}
if (process.env.VERCEL && runtimeStorageAuth !== "vercel_oidc") {
  errors.push("Vercel production runtime storage must use OIDC federation");
}
if (runtimeStorageAuth === "vercel_oidc") {
  for (const key of ["AZURE_TENANT_ID", "AZURE_CLIENT_ID"]) {
    if (!process.env[key]?.trim()) errors.push(`${key} is required for Vercel OIDC federation`);
  }
}
if ((process.env.COMPLIANCEHUB_AUDIT_PSEUDONYMIZATION_KEY || "").length < 32) {
  errors.push(
    "COMPLIANCEHUB_AUDIT_PSEUDONYMIZATION_KEY must contain at least 32 characters",
  );
}
if ((process.env.COMPLIANCEHUB_BFF_SHARED_SECRET || "").length < 32) {
  errors.push(
    "COMPLIANCEHUB_BFF_SHARED_SECRET must contain at least 32 characters",
  );
}
if ((process.env.COMPLIANCEHUB_ENTRA_CLIENT_SECRET || "").length < 32) {
  errors.push(
    "COMPLIANCEHUB_ENTRA_CLIENT_SECRET must contain at least 32 characters",
  );
}
if ((process.env.COMPLIANCEHUB_AUTH_TRANSACTION_SECRET || "").length < 32) {
  errors.push(
    "COMPLIANCEHUB_AUTH_TRANSACTION_SECRET must contain at least 32 characters",
  );
}
if (process.env.NEXT_PUBLIC_API_KEY) {
  errors.push(
    "NEXT_PUBLIC_API_KEY is forbidden because it exposes a bearer credential",
  );
}
if (process.env.COMPLIANCEHUB_ALLOW_GLOBAL_API_KEYS === "true") {
  errors.push("Global cross-tenant API keys are forbidden in production");
}
if ((process.env.COMPLIANCEHUB_LLM_PII_MODE || "block") !== "block") {
  errors.push("COMPLIANCEHUB_LLM_PII_MODE must be block in production");
}
if (process.env.COMPLIANCEHUB_LLM_PREFER_AZURE === "true") {
  for (const key of ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT"]) {
    if (!process.env[key]?.trim())
      errors.push(`${key} is required for Azure OpenAI`);
  }
  if (process.env.AZURE_OPENAI_AUTH !== "managed_identity") {
    errors.push("AZURE_OPENAI_AUTH must be managed_identity in production");
  }
  if (process.env.COMPLIANCEHUB_LLM_ASSUME_AZURE_EU !== "true") {
    errors.push(
      "Azure EU regional/Data Zone processing must be reviewed and attested",
    );
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
        errors.push(
          `${path}: public credential environment variables are forbidden`,
        );
      }
    }
  }
}

scanPublicCredentials(sourceRoot);

if (errors.length) {
  process.stderr.write(
    `Enterprise release gate failed:\n- ${errors.join("\n- ")}\n`,
  );
  process.exit(1);
}

process.stdout.write("Enterprise release gate passed\n");
