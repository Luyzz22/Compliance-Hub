import { afterEach, describe, expect, it, vi } from "vitest";

import { EntraConfigurationError, entraConfig } from "@/lib/entraAuth";

const VALID_ENV: Record<string, string> = {
  COMPLIANCEHUB_ENTRA_ENABLED: "true",
  COMPLIANCEHUB_ENTRA_TENANT_ID: "11111111-1111-4111-8111-111111111111",
  COMPLIANCEHUB_ENTRA_CLIENT_ID: "22222222-2222-4222-8222-222222222222",
  COMPLIANCEHUB_ENTRA_CLIENT_SECRET:
    "client-secret-at-least-thirty-two-characters",
  COMPLIANCEHUB_ENTRA_PROVIDER_ID: "33333333-3333-4333-8333-333333333333",
  COMPLIANCEHUB_AUTH_TRANSACTION_SECRET:
    "transaction-secret-at-least-thirty-two-bytes",
  COMPLIANCEHUB_BFF_SHARED_SECRET: "bff-secret-at-least-thirty-two-characters",
  COMPLIANCEHUB_APP_ORIGIN: "http://localhost:3000",
};

function configure(overrides: Record<string, string> = {}) {
  for (const [key, value] of Object.entries({ ...VALID_ENV, ...overrides })) {
    vi.stubEnv(key, value);
  }
}

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("Entra configuration boundary", () => {
  it("is disabled unless the operator explicitly enables it", () => {
    vi.stubEnv("COMPLIANCEHUB_ENTRA_ENABLED", "false");
    expect(() => entraConfig()).toThrow(EntraConfigurationError);
  });

  it("accepts a complete non-production configuration", () => {
    configure();
    expect(entraConfig()).toMatchObject({
      tenantId: VALID_ENV.COMPLIANCEHUB_ENTRA_TENANT_ID,
      clientId: VALID_ENV.COMPLIANCEHUB_ENTRA_CLIENT_ID,
      providerId: VALID_ENV.COMPLIANCEHUB_ENTRA_PROVIDER_ID,
      redirectUri: "http://localhost:3000/api/auth/entra/callback",
    });
  });

  it("rejects placeholder identifiers even when they are syntactically valid", () => {
    configure({
      COMPLIANCEHUB_ENTRA_TENANT_ID: "00000000-0000-0000-0000-000000000000",
    });
    expect(() => entraConfig()).toThrow("must be a non-placeholder GUID");
  });
});
