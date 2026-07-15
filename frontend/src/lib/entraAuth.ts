import "server-only";

import {
  ConfidentialClientApplication,
  CryptoProvider,
  PromptValue,
  ResponseMode,
  type IdTokenClaims,
} from "@azure/msal-node";

import {
  sealEntraTransaction,
  secureValuesEqual,
  type EntraTransaction,
} from "@/lib/entraTransaction";
import { safeReturnTo } from "@/lib/safeReturnTo";

const GUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const NIL_GUID = "00000000-0000-0000-0000-000000000000";
const SCOPES = ["openid", "profile", "email"];

export class EntraConfigurationError extends Error {}

export type EntraConfig = {
  tenantId: string;
  clientId: string;
  clientSecret: string;
  providerId: string;
  appOrigin: string;
  redirectUri: string;
  transactionSecret: string;
};

export function entraIsEnabled(): boolean {
  return process.env.COMPLIANCEHUB_ENTRA_ENABLED === "true";
}

function required(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) throw new EntraConfigurationError(`${name} is required`);
  return value;
}

function requiredGuid(name: string): string {
  const value = required(name).toLowerCase();
  if (!GUID_RE.test(value) || value === NIL_GUID) {
    throw new EntraConfigurationError(`${name} must be a non-placeholder GUID`);
  }
  return value;
}

export function entraConfig(): EntraConfig {
  if (!entraIsEnabled())
    throw new EntraConfigurationError("Entra authentication is disabled");
  const appOrigin = required("COMPLIANCEHUB_APP_ORIGIN").replace(/\/$/, "");
  const parsedOrigin = new URL(appOrigin);
  if (
    parsedOrigin.origin !== appOrigin ||
    (process.env.NODE_ENV === "production" &&
      parsedOrigin.protocol !== "https:")
  ) {
    throw new EntraConfigurationError(
      "COMPLIANCEHUB_APP_ORIGIN must be an allowed origin",
    );
  }
  const clientSecret = required("COMPLIANCEHUB_ENTRA_CLIENT_SECRET");
  const transactionSecret = required("COMPLIANCEHUB_AUTH_TRANSACTION_SECRET");
  const bffSecret = required("COMPLIANCEHUB_BFF_SHARED_SECRET");
  if (process.env.NODE_ENV === "production" && clientSecret.length < 32) {
    throw new EntraConfigurationError(
      "COMPLIANCEHUB_ENTRA_CLIENT_SECRET is too short",
    );
  }
  if (Buffer.byteLength(transactionSecret, "utf8") < 32) {
    throw new EntraConfigurationError(
      "COMPLIANCEHUB_AUTH_TRANSACTION_SECRET is too short",
    );
  }
  if (bffSecret.length < 32) {
    throw new EntraConfigurationError(
      "COMPLIANCEHUB_BFF_SHARED_SECRET is too short",
    );
  }
  return {
    tenantId: requiredGuid("COMPLIANCEHUB_ENTRA_TENANT_ID"),
    clientId: requiredGuid("COMPLIANCEHUB_ENTRA_CLIENT_ID"),
    clientSecret,
    providerId: requiredGuid("COMPLIANCEHUB_ENTRA_PROVIDER_ID"),
    appOrigin,
    redirectUri: `${appOrigin}/api/auth/entra/callback`,
    transactionSecret,
  };
}

let cachedClient: {
  key: string;
  client: ConfidentialClientApplication;
} | null = null;

function entraClient(config: EntraConfig): ConfidentialClientApplication {
  const key = `${config.tenantId}:${config.clientId}`;
  if (!cachedClient || cachedClient.key !== key) {
    cachedClient = {
      key,
      client: new ConfidentialClientApplication({
        auth: {
          clientId: config.clientId,
          authority: `https://login.microsoftonline.com/${config.tenantId}`,
          clientSecret: config.clientSecret,
        },
        system: {
          loggerOptions: {
            piiLoggingEnabled: false,
            loggerCallback: () => undefined,
          },
        },
      }),
    };
  }
  return cachedClient.client;
}

export async function createEntraAuthorization(
  requestedReturnTo: string | null,
): Promise<{ authorizationUrl: string; sealedTransaction: string }> {
  const config = entraConfig();
  const crypto = new CryptoProvider();
  const [{ verifier, challenge }, state, nonce] = await Promise.all([
    crypto.generatePkceCodes(),
    Promise.resolve(crypto.createNewGuid()),
    Promise.resolve(crypto.createNewGuid()),
  ]);
  const transaction: EntraTransaction = {
    state,
    nonce,
    codeVerifier: verifier,
    returnTo: safeReturnTo(requestedReturnTo),
    providerId: config.providerId,
    createdAt: Date.now(),
  };
  const authorizationUrl = await entraClient(config).getAuthCodeUrl({
    scopes: SCOPES,
    redirectUri: config.redirectUri,
    responseMode: ResponseMode.QUERY,
    codeChallenge: challenge,
    codeChallengeMethod: "S256",
    state,
    nonce,
    prompt: PromptValue.SELECT_ACCOUNT,
  });
  return {
    authorizationUrl,
    sealedTransaction: sealEntraTransaction(
      transaction,
      config.transactionSecret,
    ),
  };
}

export async function redeemEntraAuthorizationCode(
  code: string,
  transaction: EntraTransaction,
): Promise<{ idToken: string; claims: IdTokenClaims }> {
  const config = entraConfig();
  if (transaction.providerId !== config.providerId) {
    throw new Error("Entra provider changed during authentication");
  }
  const result = await entraClient(config).acquireTokenByCode({
    code,
    scopes: SCOPES,
    redirectUri: config.redirectUri,
    codeVerifier: transaction.codeVerifier,
  });
  const claims = result?.idTokenClaims as IdTokenClaims | undefined;
  if (
    !result?.idToken ||
    !claims ||
    !secureValuesEqual(String(claims.nonce || ""), transaction.nonce) ||
    String(claims.tid || "").toLowerCase() !== config.tenantId ||
    String(claims.aud || "").toLowerCase() !== config.clientId ||
    String(claims.ver || "") !== "2.0" ||
    !GUID_RE.test(String(claims.oid || ""))
  ) {
    throw new Error("Entra identity response validation failed");
  }
  return { idToken: result.idToken, claims };
}
