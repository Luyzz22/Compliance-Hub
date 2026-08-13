import { createHmac, timingSafeEqual } from "crypto";

import "server-only";

import { isEnterpriseProductionRuntime } from "@/lib/outboundEndpointPolicy";
import { readServerSecret } from "@/lib/serverSecret";

const COOKIE_NAME = "ch_lead_admin";
const DEFAULT_SESSION_MINUTES = 480;
const MAX_SESSION_MINUTES = 480;
const AUTOMATION_SIGNATURE_WINDOW_SECONDS = 300;

function sessionDurationMs(): number {
  const configured = Number(process.env.COMPLIANCEHUB_SESSION_TTL_MINUTES);
  const minutes = Number.isSafeInteger(configured) && configured >= 5
    ? Math.min(configured, MAX_SESSION_MINUTES)
    : DEFAULT_SESSION_MINUTES;
  return minutes * 60 * 1000;
}

function adminSecret(): string | null {
  return readServerSecret({
    environmentVariable: "LEAD_ADMIN_SECRET",
    fileEnvironmentVariable: "LEAD_ADMIN_SECRET_FILE",
    minimumBytes: 32,
    required: false,
  });
}

function gtmAlertSecret(): string | null {
  return readServerSecret({
    environmentVariable: "GTM_ALERT_SECRET",
    fileEnvironmentVariable: "GTM_ALERT_SECRET_FILE",
    minimumBytes: 32,
    required: false,
  });
}

function credentialsMatch(candidate: string, expected: string): boolean {
  const candidateBytes = Buffer.from(candidate, "utf8");
  const expectedBytes = Buffer.from(expected, "utf8");
  return (
    candidateBytes.length === expectedBytes.length &&
    timingSafeEqual(candidateBytes, expectedBytes)
  );
}

function bearerCredential(req: Request): string {
  const auth = req.headers.get("authorization") || "";
  if (auth.startsWith("Bearer ")) return auth.slice(7).trim();
  if (!isEnterpriseProductionRuntime()) {
    return new URL(req.url).searchParams.get("secret")?.trim() || "";
  }
  return "";
}

export function leadAdminIsConfigured(): boolean {
  return Boolean(adminSecret());
}

export function leadAdminOrGtmAlertSecretIsConfigured(): boolean {
  return Boolean(adminSecret() || gtmAlertSecret());
}

function verifyGtmAutomationSignature(req: Request, secret: string): boolean {
  const timestampRaw = req.headers.get("x-compliancehub-timestamp")?.trim() ?? "";
  const signatureRaw = req.headers.get("x-compliancehub-signature")?.trim() ?? "";
  if (!/^\d{10}$/.test(timestampRaw) || !signatureRaw.startsWith("v1=")) return false;
  const timestamp = Number(timestampRaw);
  const now = Math.floor(Date.now() / 1000);
  if (!Number.isSafeInteger(timestamp) || Math.abs(now - timestamp) > AUTOMATION_SIGNATURE_WINDOW_SECONDS) {
    return false;
  }
  const url = new URL(req.url);
  const canonicalRequest = `${req.method.toUpperCase()}\n${url.pathname}\n${timestampRaw}`;
  const expected = createHmac("sha256", secret).update(canonicalRequest).digest("hex");
  const candidate = signatureRaw.slice(3);
  if (!/^[a-f0-9]{64}$/.test(candidate)) return false;
  return credentialsMatch(candidate, expected);
}

export function leadAdminCredentialIsValid(candidate: string): boolean {
  const secret = adminSecret();
  return Boolean(secret && candidate && credentialsMatch(candidate, secret));
}

export function createLeadAdminSessionToken(): string | null {
  const secret = adminSecret();
  if (!secret) return null;
  const exp = Date.now() + sessionDurationMs();
  const sig = createHmac("sha256", secret).update(`v1|${exp}`).digest("hex");
  const payload = JSON.stringify({ exp, sig });
  return Buffer.from(payload, "utf8").toString("base64url");
}

export function verifyLeadAdminSession(token: string | null | undefined): boolean {
  const secret = adminSecret();
  if (!secret || !token?.trim()) return false;
  try {
    const raw = Buffer.from(token.trim(), "base64url").toString("utf8");
    const { exp, sig } = JSON.parse(raw) as { exp?: number; sig?: string };
    if (typeof exp !== "number" || typeof sig !== "string") return false;
    if (Date.now() > exp) return false;
    const expected = createHmac("sha256", secret).update(`v1|${exp}`).digest("hex");
    const a = Buffer.from(sig, "hex");
    const b = Buffer.from(expected, "hex");
    if (a.length !== b.length) return false;
    return timingSafeEqual(a, b);
  } catch {
    return false;
  }
}

export const LEAD_ADMIN_COOKIE_NAME = COOKIE_NAME;

export function leadAdminCookieOptions(): {
  httpOnly: boolean;
  secure: boolean;
  sameSite: "strict";
  path: string;
  maxAge: number;
} {
  return {
    httpOnly: true,
    secure: isEnterpriseProductionRuntime(),
    sameSite: "strict",
    path: "/",
    maxAge: Math.floor(sessionDurationMs() / 1000),
  };
}

/**
 * Bearer-Secret oder gültiges Admin-Session-Cookie; Query-Secrets nur in Entwicklung.
 */
export function isLeadAdminAuthorized(req: Request): boolean {
  const secret = adminSecret();
  if (!secret) return false;

  const bearer = bearerCredential(req);
  if (bearer && credentialsMatch(bearer, secret)) return true;

  const cookieHeader = req.headers.get("cookie") ?? "";
  const match = cookieHeader.split(";").map((s) => s.trim()).find((s) => s.startsWith(`${COOKIE_NAME}=`));
  if (!match) return false;
  const value = decodeURIComponent(match.slice(`${COOKIE_NAME}=`.length));
  return verifyLeadAdminSession(value);
}

/**
 * Lead-Admin session or a timestamped automation HMAC (Cron/n8n without a cookie).
 */
export function isLeadAdminOrGtmAlertSecretAuthorized(req: Request): boolean {
  if (isLeadAdminAuthorized(req)) return true;
  const gtm = gtmAlertSecret();
  if (!gtm) return false;
  return verifyGtmAutomationSignature(req, gtm);
}
