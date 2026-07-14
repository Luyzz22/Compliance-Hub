import { timingSafeEqual } from "node:crypto";

const MAX_LOGIN_BODY_BYTES = 16 * 1024;

function normalizedOrigin(value: string): string | null {
  try {
    return new URL(value).origin;
  } catch {
    return null;
  }
}

export function hasAllowedMutationOrigin(
  requestUrl: string,
  originHeader: string | null,
  configuredOrigin: string | undefined,
  production: boolean,
): boolean {
  const origin = originHeader ? normalizedOrigin(originHeader) : null;
  if (!origin) return false;

  const configured = configuredOrigin
    ? normalizedOrigin(configuredOrigin.trim())
    : null;
  if (configured) return origin === configured;
  if (production) return false;

  return origin === normalizedOrigin(requestUrl);
}

export function csrfTokensMatch(
  cookieToken: string | undefined,
  headerToken: string | null,
): boolean {
  if (!cookieToken || !headerToken) return false;
  const left = Buffer.from(cookieToken, "utf8");
  const right = Buffer.from(headerToken, "utf8");
  return left.length === right.length && timingSafeEqual(left, right);
}

export function parseLoginBody(raw: string): {
  email: string;
  password: string;
  tenant_id?: string;
} | null {
  if (!raw || Buffer.byteLength(raw, "utf8") > MAX_LOGIN_BODY_BYTES) return null;

  let body: unknown;
  try {
    body = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!body || typeof body !== "object" || Array.isArray(body)) return null;

  const candidate = body as Record<string, unknown>;
  const email = typeof candidate.email === "string" ? candidate.email.trim() : "";
  const password = typeof candidate.password === "string" ? candidate.password : "";
  const tenant =
    typeof candidate.tenant_id === "string" ? candidate.tenant_id.trim() : "";
  if (!email || email.length > 320 || !password || password.length > 1024) return null;
  if (tenant.length > 255) return null;
  return tenant ? { email, password, tenant_id: tenant } : { email, password };
}
