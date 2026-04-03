import { createHmac, timingSafeEqual } from "crypto";

import "server-only";

const COOKIE_NAME = "ch_lead_admin";
const SESSION_MS = 7 * 24 * 60 * 60 * 1000;

function adminSecret(): string | null {
  return process.env.LEAD_ADMIN_SECRET?.trim() ?? null;
}

export function createLeadAdminSessionToken(): string | null {
  const secret = adminSecret();
  if (!secret) return null;
  const exp = Date.now() + SESSION_MS;
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
  sameSite: "lax";
  path: string;
  maxAge: number;
} {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: Math.floor(SESSION_MS / 1000),
  };
}

/**
 * Bearer / Query-Secret (wie Wave 25) oder gültige Admin-Session-Cookie.
 */
export function isLeadAdminAuthorized(req: Request): boolean {
  const secret = adminSecret();
  if (!secret) return false;

  const auth = req.headers.get("authorization");
  const url = new URL(req.url);
  const qSecret = url.searchParams.get("secret");
  const bearer =
    auth?.startsWith("Bearer ") ? auth.slice(7).trim() : qSecret?.trim() ?? "";
  if (bearer === secret) return true;

  const cookieHeader = req.headers.get("cookie") ?? "";
  const match = cookieHeader.split(";").map((s) => s.trim()).find((s) => s.startsWith(`${COOKIE_NAME}=`));
  if (!match) return false;
  const value = decodeURIComponent(match.slice(`${COOKIE_NAME}=`.length));
  return verifyLeadAdminSession(value);
}

/**
 * Lead-Admin **oder** separates Automation-Secret (Wave 32 – Cron/n8n ohne Session-Cookie).
 */
export function isLeadAdminOrGtmAlertSecretAuthorized(req: Request): boolean {
  if (isLeadAdminAuthorized(req)) return true;
  const gtm = process.env.GTM_ALERT_SECRET?.trim();
  if (!gtm) return false;
  const auth = req.headers.get("authorization");
  const url = new URL(req.url);
  const q = url.searchParams.get("secret");
  const bearer = auth?.startsWith("Bearer ") ? auth.slice(7).trim() : q?.trim() ?? "";
  return bearer === gtm;
}
