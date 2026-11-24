import { afterEach, describe, expect, it, vi } from "vitest";
import type { Configuration } from "@azure/msal-node";

import { redeemEntraAuthorizationCode } from "@/lib/entraAuth";
import type { EntraTransaction } from "@/lib/entraTransaction";

const transport = vi.hoisted(() => ({
  nonce: "synthetic-original-nonce" as string | undefined,
  tokenRequests: [] as string[],
}));

// Keep the real SDK code-redemption and response validation. Only replace its
// network transport and discovery metadata with synthetic, offline fixtures.
vi.mock("@azure/msal-node", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@azure/msal-node")>();
  return {
    ...actual,
    ConfidentialClientApplication: class
      extends actual.ConfidentialClientApplication
    {
      constructor(config: Configuration) {
        const authority = config.auth.authority!;
        const tenantId = authority.split("/").at(-1)!;
        const metadata = {
          authorization_endpoint: authority + "/oauth2/v2.0/authorize",
          token_endpoint: authority + "/oauth2/v2.0/token",
          issuer: authority + "/v2.0",
          jwks_uri: authority + "/discovery/v2.0/keys",
          end_session_endpoint: authority + "/oauth2/v2.0/logout",
        };
        const encode = (value: unknown) =>
          Buffer.from(JSON.stringify(value)).toString("base64url");
        super({
          ...config,
          auth: {
            ...config.auth,
            authorityMetadata: JSON.stringify(metadata),
            cloudDiscoveryMetadata: JSON.stringify({
              tenant_discovery_endpoint: metadata.authorization_endpoint,
              metadata: [
                {
                  preferred_network: "login.microsoftonline.com",
                  preferred_cache: "login.windows.net",
                  aliases: [
                    "login.microsoftonline.com",
                    "login.windows.net",
                    "sts.windows.net",
                  ],
                },
              ],
            }),
          },
          system: {
            ...config.system,
            networkClient: {
              async sendGetRequestAsync() {
                throw new Error(
                  "Unexpected network discovery in offline SDK test",
                );
              },
              async sendPostRequestAsync<T>(url: string) {
                transport.tokenRequests.push(url);
                const now = Math.floor(Date.now() / 1000);
                const claims = {
                  iss: metadata.issuer,
                  aud: config.auth.clientId,
                  iat: now,
                  exp: now + 3600,
                  nonce: transport.nonce,
                  tid: tenantId,
                  oid: "44444444-4444-4444-8444-444444444444",
                  sub: "synthetic-subject",
                  ver: "2.0",
                  preferred_username: "synthetic@example.invalid",
                };
                return {
                  status: 200,
                  headers: {},
                  body: {
                    token_type: "Bearer",
                    scope: "openid profile email",
                    expires_in: 3600,
                    ext_expires_in: 3600,
                    access_token: "synthetic-access-token",
                    refresh_token: "synthetic-refresh-token",
                    id_token: [
                      encode({ alg: "RS256", typ: "JWT" }),
                      encode(claims),
                      "synthetic-signature",
                    ].join("."),
                    client_info: encode({
                      uid: "synthetic-user",
                      utid: tenantId,
                    }),
                  } as T,
                };
              },
            },
          },
        });
      }
    },
  };
});

const tenantId = "11111111-1111-4111-8111-111111111111";
const providerId = "33333333-3333-4333-8333-333333333333";
const transaction: EntraTransaction = {
  state: "synthetic-state",
  nonce: "synthetic-original-nonce",
  codeVerifier: "synthetic-code-verifier-000000000000000000000000000000",
  returnTo: "/board/executive-dashboard",
  providerId,
  createdAt: 0,
};

function configure() {
  const environment = {
    COMPLIANCEHUB_ENTRA_ENABLED: "true",
    COMPLIANCEHUB_ENTRA_TENANT_ID: tenantId,
    COMPLIANCEHUB_ENTRA_CLIENT_ID: "22222222-2222-4222-8222-222222222222",
    COMPLIANCEHUB_ENTRA_CLIENT_SECRET:
      "synthetic-client-secret-at-least-thirty-two-bytes",
    COMPLIANCEHUB_ENTRA_PROVIDER_ID: providerId,
    COMPLIANCEHUB_AUTH_TRANSACTION_SECRET:
      "synthetic-transaction-secret-at-least-thirty-two-bytes",
    COMPLIANCEHUB_BFF_SHARED_SECRET:
      "synthetic-bff-secret-at-least-thirty-two-bytes",
    COMPLIANCEHUB_APP_ORIGIN: "http://localhost:3000",
  };
  for (const [key, value] of Object.entries(environment))
    vi.stubEnv(key, value);
}

afterEach(() => {
  vi.unstubAllEnvs();
  transport.nonce = transaction.nonce;
  transport.tokenRequests.length = 0;
});

describe("Entra redemption through the real MSAL response validation", () => {
  it("redeems a token bound to the original authorization nonce", async () => {
    configure();
    await expect(
      redeemEntraAuthorizationCode("synthetic-code", transaction),
    ).resolves.toMatchObject({
      claims: { nonce: transaction.nonce, tid: tenantId },
    });
    expect(
      transport.tokenRequests.map((url) => {
        const parsed = new URL(url);
        return parsed.origin + parsed.pathname;
      }),
    ).toEqual([
      "https://login.microsoftonline.com/" + tenantId + "/oauth2/v2.0/token",
    ]);
  });

  it.each(["different-nonce", undefined])(
    "rejects an unbound token nonce: %s",
    async (nonce) => {
      configure();
      transport.nonce = nonce;
      await expect(
        redeemEntraAuthorizationCode("synthetic-code", transaction),
      ).rejects.toThrow(/nonce|identity response validation failed/i);
      expect(transport.tokenRequests).toHaveLength(1);
    },
  );
});
