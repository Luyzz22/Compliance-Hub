import { afterEach, describe, expect, it, vi } from "vitest";
import { createHash } from "node:crypto";
import {
  ConfidentialClientApplication,
  type AuthenticationResult,
} from "@azure/msal-node";

import {
  EntraConfigurationError,
  entraConfig,
  createEntraAuthorization,
  redeemEntraAuthorizationCode,
} from "@/lib/entraAuth";
import {
  openEntraTransaction,
  type EntraTransaction,
} from "@/lib/entraTransaction";

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
  vi.restoreAllMocks();
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

describe("Entra authorization with the patched SDK", () => {
  const transaction: EntraTransaction = {
    state: "synthetic-state-000000000000000000000",
    nonce: "synthetic-nonce-000000000000000000000",
    codeVerifier: "synthetic-verifier-000000000000000000000000000000",
    returnTo: "/",
    providerId: VALID_ENV.COMPLIANCEHUB_ENTRA_PROVIDER_ID,
    createdAt: 0,
  };

  function tokenResult(overrides: Record<string, unknown> = {}) {
    return {
      idToken: "synthetic-id-token",
      idTokenClaims: {
        nonce: transaction.nonce,
        tid: VALID_ENV.COMPLIANCEHUB_ENTRA_TENANT_ID,
        aud: VALID_ENV.COMPLIANCEHUB_ENTRA_CLIENT_ID,
        ver: "2.0",
        oid: "44444444-4444-4444-8444-444444444444",
        ...overrides,
      },
    } as AuthenticationResult;
  }

  it("binds the sealed transaction to real SDK-generated PKCE, state and nonce", async () => {
    configure();
    const request = vi
      .spyOn(ConfidentialClientApplication.prototype, "getAuthCodeUrl")
      .mockResolvedValue("https://login.microsoftonline.com/synthetic");
    const authorization = await createEntraAuthorization(
      "https://example.invalid/redirect",
    );
    const opened = openEntraTransaction(
      authorization.sealedTransaction,
      VALID_ENV.COMPLIANCEHUB_AUTH_TRANSACTION_SECRET,
    );
    expect(opened).not.toBeNull();
    expect(opened?.returnTo).toBe("/board/executive-dashboard");
    expect(request).toHaveBeenCalledWith(
      expect.objectContaining({
        state: opened?.state,
        nonce: opened?.nonce,
        codeChallenge: createHash("sha256")
          .update(opened!.codeVerifier)
          .digest("base64url"),
        codeChallengeMethod: "S256",
        redirectUri: "http://localhost:3000/api/auth/entra/callback",
      }),
    );
  });

  it("redeems the bound code while retaining the identity checks", async () => {
    configure();
    const redeem = vi
      .spyOn(ConfidentialClientApplication.prototype, "acquireTokenByCode")
      .mockResolvedValue(tokenResult());
    await expect(
      redeemEntraAuthorizationCode("synthetic-code", transaction),
    ).resolves.toMatchObject({ idToken: "synthetic-id-token" });
    expect(redeem).toHaveBeenCalledWith(
      expect.objectContaining({
        code: "synthetic-code",
        codeVerifier: transaction.codeVerifier,
        redirectUri: "http://localhost:3000/api/auth/entra/callback",
      }),
    );
  });

  it.each([
    { nonce: "other" },
    { tid: "other" },
    { aud: "other" },
    { ver: "1.0" },
    { oid: "not-a-guid" },
  ])("rejects identity claims outside the transaction: %j", async (claims) => {
    configure();
    vi.spyOn(
      ConfidentialClientApplication.prototype,
      "acquireTokenByCode",
    ).mockResolvedValue(tokenResult(claims));
    await expect(
      redeemEntraAuthorizationCode("synthetic-code", transaction),
    ).rejects.toThrow("identity response validation failed");
  });

  it("does not redeem a transaction from another provider", async () => {
    configure();
    const redeem = vi.spyOn(
      ConfidentialClientApplication.prototype,
      "acquireTokenByCode",
    );
    await expect(
      redeemEntraAuthorizationCode("synthetic-code", {
        ...transaction,
        providerId: "other",
      }),
    ).rejects.toThrow("provider changed");
    expect(redeem).not.toHaveBeenCalled();
  });
});
