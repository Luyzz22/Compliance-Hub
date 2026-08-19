import { spawnSync } from "node:child_process";

import { describe, expect, it } from "vitest";

const sensitiveEnvironmentPattern =
  /^(?:COMPLIANCEHUB_|NEXT_PUBLIC_|POSTGRES_|SUPABASE_|AZURE_|TEMPORAL_|DATABASE_URL$|PGPASSWORD$|VERCEL)/;

function reviewedDate(): string {
  return new Date().toISOString().slice(0, 10);
}

function publicSiteEnvironment(): NodeJS.ProcessEnv {
  const cleanEnvironment = Object.fromEntries(
    Object.entries(process.env).filter(
      ([key]) => !sensitiveEnvironmentPattern.test(key),
    ),
  );
  return {
    ...cleanEnvironment,
    // `Object.fromEntries` widens to a plain index signature, which drops the required
    // `NODE_ENV` from `ProcessEnv`. The value survives the filter at runtime — it is
    // restated here so the object still satisfies the type.
    NODE_ENV: process.env.NODE_ENV ?? "test",
    COMPLIANCEHUB_RELEASE_CHANNEL: "production",
    COMPLIANCEHUB_RELEASE_PROFILE: "public_site",
    COMPLIANCEHUB_APP_ORIGIN: "https://complywithai.de",
    COMPLIANCEHUB_TRUSTED_HOSTS: "complywithai.de",
    COMPLIANCEHUB_LEGAL_ENTITY_NAME: "Example GmbH",
    COMPLIANCEHUB_LEGAL_REPRESENTATIVE: "Erika Beispiel",
    COMPLIANCEHUB_LEGAL_STREET: "Beispielweg 1",
    COMPLIANCEHUB_LEGAL_POSTAL_CODE: "10115",
    COMPLIANCEHUB_LEGAL_CITY: "Berlin",
    COMPLIANCEHUB_LEGAL_COUNTRY: "Deutschland",
    COMPLIANCEHUB_LEGAL_EMAIL: "legal@example.invalid",
    COMPLIANCEHUB_LEGAL_REGISTER_COURT: "Amtsgericht Berlin",
    COMPLIANCEHUB_LEGAL_REGISTER_NUMBER: "HRB 12345",
    COMPLIANCEHUB_LEGAL_VAT_ID: "DE123456789",
    COMPLIANCEHUB_PRIVACY_EMAIL: "privacy@example.invalid",
    COMPLIANCEHUB_PRIVACY_NOTICE_VERSION: "test-1",
    COMPLIANCEHUB_PRIVACY_REVIEWED_AT: reviewedDate(),
    COMPLIANCEHUB_PRIVACY_LOG_RETENTION_DAYS: "14",
    COMPLIANCEHUB_PRIVACY_LEAD_RETENTION_DAYS: "180",
    COMPLIANCEHUB_SECURITY_CONTACT: "mailto:security@example.invalid",
    COMPLIANCEHUB_LEGAL_PUBLISH_READY: "true",
    COMPLIANCEHUB_PUBLIC_SITE_READY: "true",
  };
}

function runGate(environment: NodeJS.ProcessEnv) {
  return spawnSync(process.execPath, ["scripts/verify-enterprise-readiness.mjs"], {
    cwd: process.cwd(),
    env: environment,
    encoding: "utf8",
  });
}

describe("enterprise release gate profiles", () => {
  it("accepts a reviewed stateless public-site release", () => {
    const result = runGate(publicSiteEnvironment());

    expect(result.status, result.stderr).toBe(0);
    expect(result.stdout).toContain("passed (public_site)");
  });

  it("starts the public-site runtime image, which sets the preflight flag itself", () => {
    // frontend/Dockerfile.hetzner setzt COMPLIANCEHUB_RUNTIME_PREFLIGHT=true und ruft
    // das Gate im CMD auf. Fehlt die Variable auf der Allowlist, bricht jeder
    // Containerstart ab — die Website wäre nicht ausrollbar.
    const result = runGate({
      ...publicSiteEnvironment(),
      COMPLIANCEHUB_RUNTIME_PREFLIGHT: "true",
    });

    expect(result.status, result.stderr).toBe(0);
    expect(result.stdout).toContain("passed (public_site)");
  });

  it("rejects inherited database credentials in the public-site release", () => {
    const result = runGate({
      ...publicSiteEnvironment(),
      POSTGRES_URL: "postgres://forbidden.invalid/database",
    });

    expect(result.status).toBe(1);
    expect(result.stderr).toContain(
      "POSTGRES_URL is forbidden in the stateless public_site release",
    );
  });

  it("rejects Vercel runtime metadata and application browser variables", () => {
    const platformResult = runGate({
      ...publicSiteEnvironment(),
      VERCEL_ENV: "production",
    });
    const applicationResult = runGate({
      ...publicSiteEnvironment(),
      NEXT_PUBLIC_APPLICATION_FLAG: "true",
    });

    expect(platformResult.status).toBe(1);
    expect(platformResult.stderr).toContain("Vercel runtime variables are forbidden");
    expect(applicationResult.status).toBe(1);
    expect(applicationResult.stderr).toContain(
      "NEXT_PUBLIC_APPLICATION_FLAG is forbidden in the stateless public_site release",
    );
  });

  it("requires explicit legal approval for the public-site release", () => {
    const environment = publicSiteEnvironment();
    delete environment.COMPLIANCEHUB_LEGAL_PUBLISH_READY;
    const result = runGate(environment);

    expect(result.status).toBe(1);
    expect(result.stderr).toContain("documented legal review");
  });

  it("rejects unresolved legal placeholders", () => {
    const result = runGate({
      ...publicSiteEnvironment(),
      COMPLIANCEHUB_LEGAL_STREET: "replace-after-legal-review",
    });

    expect(result.status).toBe(1);
    expect(result.stderr).toContain(
      "COMPLIANCEHUB_LEGAL_STREET must contain a reviewed production value",
    );
  });

  it("does not weaken the enterprise profile requirements", () => {
    const result = runGate({
      ...publicSiteEnvironment(),
      COMPLIANCEHUB_RELEASE_PROFILE: "enterprise",
    });

    expect(result.status).toBe(1);
    expect(result.stderr).toContain("COMPLIANCEHUB_API_BASE_URL is required");
    expect(result.stderr).toContain("COMPLIANCEHUB_ENTRA_ENABLED must be true");
  });

  it("rejects a browser-visible backend origin in enterprise production", () => {
    const result = runGate({
      ...publicSiteEnvironment(),
      COMPLIANCEHUB_RELEASE_PROFILE: "enterprise",
      NEXT_PUBLIC_API_BASE_URL: "https://api.example.invalid",
    });

    expect(result.status).toBe(1);
    expect(result.stderr).toContain(
      "NEXT_PUBLIC_API_BASE_URL is forbidden; authenticated browser traffic must use the same-origin BFF",
    );
  });

  it("rejects local password identity flags in enterprise production", () => {
    const result = runGate({
      ...publicSiteEnvironment(),
      COMPLIANCEHUB_RELEASE_PROFILE: "enterprise",
      COMPLIANCEHUB_PASSWORD_LOGIN_ENABLED: "true",
      COMPLIANCEHUB_SELF_REGISTRATION_ENABLED: "true",
    });

    expect(result.status).toBe(1);
    expect(result.stderr).toContain(
      "COMPLIANCEHUB_PASSWORD_LOGIN_ENABLED must remain disabled",
    );
    expect(result.stderr).toContain(
      "COMPLIANCEHUB_SELF_REGISTRATION_ENABLED must remain disabled",
    );
  });

  it("rejects forbidden CRM provider configuration in enterprise production", () => {
    const result = runGate({
      ...publicSiteEnvironment(),
      COMPLIANCEHUB_RELEASE_PROFILE: "enterprise",
      HUBSPOT_ACCESS_TOKEN: "forbidden-token",
    });

    expect(result.status).toBe(1);
    expect(result.stderr).toContain(
      "HUBSPOT_ACCESS_TOKEN is forbidden by the sovereign production provider policy",
    );
  });

  it("rejects direct US LLM and dependency telemetry configuration", () => {
    const result = runGate({
      ...publicSiteEnvironment(),
      COMPLIANCEHUB_RELEASE_PROFILE: "enterprise",
      OPENAI_API_KEY: "forbidden-token",
      HAYSTACK_TELEMETRY_ENABLED: "true",
      STRIPE_SECRET_KEY: "forbidden-billing-token",
    });

    expect(result.status).toBe(1);
    expect(result.stderr).toContain("OPENAI_API_KEY is forbidden");
    expect(result.stderr).toContain("HAYSTACK_TELEMETRY_ENABLED must be false");
    expect(result.stderr).toContain(
      "STRIPE_SECRET_KEY is forbidden by the sovereign production provider policy",
    );
  });

  it("rejects a non-Azure endpoint on the Azure exception path", () => {
    const result = runGate({
      ...publicSiteEnvironment(),
      COMPLIANCEHUB_RELEASE_PROFILE: "enterprise",
      COMPLIANCEHUB_SOVEREIGNTY_MODE: "standard_dach",
      COMPLIANCEHUB_LLM_PREFER_AZURE: "true",
      AZURE_OPENAI_ENDPOINT: "https://api.openai.com",
      AZURE_OPENAI_DEPLOYMENT: "approved-deployment",
    });

    expect(result.status).toBe(1);
    expect(result.stderr).toContain(
      "AZURE_OPENAI_ENDPOINT must be an approved bare Azure HTTPS endpoint",
    );
  });

  it("rejects Temporal Cloud even when its hostname is explicitly allowlisted", () => {
    const result = runGate({
      ...publicSiteEnvironment(),
      COMPLIANCEHUB_RELEASE_PROFILE: "enterprise",
      COMPLIANCEHUB_TEMPORAL_ENABLED: "true",
      COMPLIANCEHUB_TEMPORAL_ALLOWED_HOSTS: "namespace.tmprl.cloud",
      TEMPORAL_ADDRESS: "namespace.tmprl.cloud:7233",
    });

    expect(result.status).toBe(1);
    expect(result.stderr).toContain(
      "Enabled Temporal must use an exact allowlisted self-hosted host:port endpoint",
    );
  });
});
