import "server-only";

import {
  ClientAssertionCredential,
  DefaultAzureCredential,
  ManagedIdentityCredential,
  type TokenCredential,
} from "@azure/identity";
import { getVercelOidcToken } from "@vercel/oidc";

export type AzureAuthMode = "managed_identity" | "vercel_oidc" | "default";
export type AzureIdentityEnvironment = Readonly<Record<string, string | undefined>>;

export class AzureIdentityConfigurationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AzureIdentityConfigurationError";
  }
}

function isProductionRuntime(env: AzureIdentityEnvironment): boolean {
  return env.NODE_ENV === "production" || Boolean(env.VERCEL);
}

function requiredEnv(
  name: string,
  env: AzureIdentityEnvironment,
  ErrorType: new (message: string) => Error = AzureIdentityConfigurationError,
): string {
  const value = env[name]?.trim();
  if (!value) throw new ErrorType(`${name} is required`);
  return value;
}

export function resolveAzureAuthMode(
  env: AzureIdentityEnvironment = process.env,
): AzureAuthMode {
  const configured = env.COMPLIANCEHUB_RUNTIME_STORAGE_AUTH?.trim().toLowerCase();
  if (
    configured === "managed_identity" ||
    configured === "vercel_oidc" ||
    configured === "default"
  ) {
    if (configured === "default" && isProductionRuntime(env)) {
      throw new AzureIdentityConfigurationError(
        "Default Azure credential chaining is forbidden in production",
      );
    }
    return configured;
  }
  if (configured) {
    throw new AzureIdentityConfigurationError("Unsupported Azure authentication mode");
  }
  if (env.VERCEL) return "vercel_oidc";
  if (env.NODE_ENV === "production") return "managed_identity";
  return "default";
}

export function createAzureTokenCredential(
  env: AzureIdentityEnvironment = process.env,
  ErrorType: new (message: string) => Error = AzureIdentityConfigurationError,
): TokenCredential {
  let authMode: AzureAuthMode;
  try {
    authMode = resolveAzureAuthMode(env);
  } catch (error) {
    if (error instanceof AzureIdentityConfigurationError) {
      throw new ErrorType(error.message);
    }
    throw error;
  }
  if (authMode === "managed_identity") {
    const clientId = env.AZURE_CLIENT_ID?.trim();
    return new ManagedIdentityCredential(clientId ? { clientId } : undefined);
  }
  if (authMode === "vercel_oidc") {
    return new ClientAssertionCredential(
      requiredEnv("AZURE_TENANT_ID", env, ErrorType),
      requiredEnv("AZURE_CLIENT_ID", env, ErrorType),
      getVercelOidcToken,
    );
  }
  return new DefaultAzureCredential();
}
