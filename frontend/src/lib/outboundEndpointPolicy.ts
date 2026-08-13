import "server-only";

const FORBIDDEN_PRODUCTION_HOST_SUFFIXES = [
  "hubapi.com",
  "hubspot.com",
  "pipedrive.com",
  "vercel.app",
  "vercel.com",
  "neon.tech",
  "stripe.com",
  "posthog.com",
  "sentry.io",
] as const;

export function isEnterpriseProductionRuntime(): boolean {
  return (
    process.env.NODE_ENV === "production" ||
    process.env.COMPLIANCEHUB_RELEASE_CHANNEL === "production"
  );
}

function allowedWebhookHosts(): Set<string> {
  return new Set(
    (process.env.COMPLIANCEHUB_OUTBOUND_WEBHOOK_ALLOWED_HOSTS || "")
      .split(",")
      .map((host) => host.trim().toLowerCase())
      .filter(Boolean),
  );
}

function hostMatchesSuffix(hostname: string, suffix: string): boolean {
  return hostname === suffix || hostname.endsWith(`.${suffix}`);
}

export function approvedOutboundWebhookUrl(raw: string, variableName: string): string {
  let parsed: URL;
  try {
    parsed = new URL(raw);
  } catch {
    throw new Error(`${variableName} must be a valid absolute URL`);
  }

  if (parsed.username || parsed.password || parsed.hash || parsed.search) {
    throw new Error(
      `${variableName} must not contain credentials, query parameters or fragments`,
    );
  }
  if (!isEnterpriseProductionRuntime()) return parsed.toString();
  if (parsed.protocol !== "https:") {
    throw new Error(`${variableName} must use HTTPS in production`);
  }

  const hostname = parsed.hostname.toLowerCase();
  if (
    FORBIDDEN_PRODUCTION_HOST_SUFFIXES.some((suffix) =>
      hostMatchesSuffix(hostname, suffix),
    )
  ) {
    throw new Error(`${variableName} targets a provider forbidden by the sovereign profile`);
  }
  if (!allowedWebhookHosts().has(hostname)) {
    throw new Error(
      `${variableName} host must be listed in COMPLIANCEHUB_OUTBOUND_WEBHOOK_ALLOWED_HOSTS`,
    );
  }
  return parsed.toString();
}

export function approvedPrivateServiceBaseUrl(
  raw: string,
  variableName: string,
  allowlistVariable: string,
): string {
  let parsed: URL;
  try {
    parsed = new URL(raw);
  } catch {
    throw new Error(`${variableName} must be a valid absolute URL`);
  }
  if (
    !["http:", "https:"].includes(parsed.protocol) ||
    parsed.username ||
    parsed.password ||
    parsed.pathname !== "/" ||
    parsed.search ||
    parsed.hash
  ) {
    throw new Error(
      `${variableName} must be a bare HTTP(S) origin without credentials or parameters`,
    );
  }
  if (!isEnterpriseProductionRuntime()) return parsed.origin;

  const hostname = parsed.hostname.toLowerCase();
  if (
    FORBIDDEN_PRODUCTION_HOST_SUFFIXES.some((suffix) =>
      hostMatchesSuffix(hostname, suffix),
    )
  ) {
    throw new Error(`${variableName} targets a provider forbidden by the sovereign profile`);
  }
  const allowedHosts = new Set(
    (process.env[allowlistVariable] || "")
      .split(",")
      .map((host) => host.trim().toLowerCase())
      .filter(Boolean),
  );
  if (!allowedHosts.has(hostname)) {
    throw new Error(`${variableName} host must be listed in ${allowlistVariable}`);
  }
  return parsed.origin;
}

export function approvedVersionedApiPath(path: string): string {
  const internalOrigin = "http://compliancehub.internal";
  let parsed: URL;
  try {
    parsed = new URL(path, internalOrigin);
  } catch {
    throw new Error("Compliance Hub API path must be a valid relative URL");
  }
  if (
    !path.startsWith("/api/v1/") ||
    parsed.origin !== internalOrigin ||
    !parsed.pathname.startsWith("/api/v1/") ||
    parsed.hash ||
    /[\\\u0000-\u001f\u007f]/u.test(path)
  ) {
    throw new Error("Only normalized versioned Compliance Hub API routes are allowed");
  }
  return `${parsed.pathname}${parsed.search}`;
}

export function crmProviderIsForbiddenInProduction(
  provider: "hubspot" | "pipedrive",
): boolean {
  return isEnterpriseProductionRuntime() && (provider === "hubspot" || provider === "pipedrive");
}
