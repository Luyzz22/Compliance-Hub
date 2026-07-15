import { spawnSync } from "node:child_process";

import { describe, expect, it } from "vitest";

const sensitiveEnvironmentPattern =
  /^(?:COMPLIANCEHUB_|NEXT_PUBLIC_|POSTGRES_|SUPABASE_|AZURE_|DATABASE_URL$|PGPASSWORD$|VERCEL)/;

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
    VERCEL_ENV: "production",
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

  it("requires explicit legal approval for the public-site release", () => {
    const environment = publicSiteEnvironment();
    delete environment.COMPLIANCEHUB_LEGAL_PUBLISH_READY;
    const result = runGate(environment);

    expect(result.status).toBe(1);
    expect(result.stderr).toContain("documented legal review");
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
});
