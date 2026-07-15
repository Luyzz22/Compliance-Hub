const CSP_NONCE_PATTERN = /^[A-Za-z0-9+/]+={0,2}$/;

export const CSP_REPORT_ENDPOINT = "/api/security/csp-report";
export const CSP_REPORTING_GROUP = "csp-endpoint";

function safeOrigin(value: string | undefined): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:"
      ? url.origin
      : null;
  } catch {
    return null;
  }
}

export function createCspNonce(): string {
  return Buffer.from(crypto.randomUUID()).toString("base64");
}

export function buildContentSecurityPolicy({
  nonce,
  development,
  apiBaseUrl,
}: {
  nonce: string;
  development: boolean;
  apiBaseUrl?: string;
}): string {
  if (nonce.length < 24 || !CSP_NONCE_PATTERN.test(nonce)) {
    throw new Error("CSP nonce must be an unpredictable base64 value");
  }

  const apiOrigin = safeOrigin(apiBaseUrl);
  const connectSources = [
    "'self'",
    ...(apiOrigin ? [apiOrigin] : []),
    ...(development ? ["ws:"] : []),
  ].join(" ");
  const scriptSources = [
    "'self'",
    `'nonce-${nonce}'`,
    "'strict-dynamic'",
    ...(development ? ["'unsafe-eval'"] : []),
  ].join(" ");
  const styleSources = ["'self'", `'nonce-${nonce}'`].join(" ");

  return [
    "default-src 'self'",
    "base-uri 'self'",
    "frame-ancestors 'none'",
    "frame-src 'none'",
    "form-action 'self'",
    "object-src 'none'",
    `script-src ${scriptSources}`,
    "script-src-attr 'none'",
    `style-src ${styleSources}`,
    "style-src-attr 'none'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    `connect-src ${connectSources}`,
    "media-src 'self'",
    "worker-src 'self' blob:",
    "manifest-src 'self'",
    ...(development ? [] : ["upgrade-insecure-requests"]),
    ...(development
      ? []
      : [
          `report-uri ${CSP_REPORT_ENDPOINT}`,
          `report-to ${CSP_REPORTING_GROUP}`,
        ]),
  ].join("; ");
}
