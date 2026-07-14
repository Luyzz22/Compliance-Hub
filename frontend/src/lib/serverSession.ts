import "server-only";

import { randomBytes } from "node:crypto";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { CSRF_COOKIE_NAME, SESSION_COOKIE_NAME } from "@/lib/authConstants";
import { csrfTokensMatch, hasAllowedMutationOrigin } from "@/lib/sessionSecurity";

const DEFAULT_SESSION_MAX_AGE_SECONDS = 8 * 60 * 60;
const BACKEND_TIMEOUT_MS = 10_000;

export type PublicSession = {
  session_id: string;
  user_id: string;
  email: string;
  display_name?: string | null;
  tenant_id: string;
  role: string;
  auth_method: string;
};

export function complianceApiBaseUrl(): string {
  const configured = process.env.COMPLIANCEHUB_API_BASE_URL?.trim();
  if (configured) return configured.replace(/\/$/, "");
  if (process.env.NODE_ENV !== "production") return "http://localhost:8000";
  throw new Error("COMPLIANCEHUB_API_BASE_URL is required");
}

export function bffBackendHeaders(): Record<string, string> {
  const secret = process.env.COMPLIANCEHUB_BFF_SHARED_SECRET?.trim();
  if (!secret) {
    if (process.env.NODE_ENV === "production") {
      throw new Error("COMPLIANCEHUB_BFF_SHARED_SECRET is required");
    }
    return {};
  }
  return { "x-bff-secret": secret };
}

export function mutationRequestIsTrusted(request: NextRequest): boolean {
  return hasAllowedMutationOrigin(
    request.url,
    request.headers.get("origin"),
    process.env.COMPLIANCEHUB_APP_ORIGIN,
    process.env.NODE_ENV === "production",
  );
}

export function mutationCsrfIsValid(request: NextRequest): boolean {
  return (
    mutationRequestIsTrusted(request) &&
    csrfTokensMatch(
      request.cookies.get(CSRF_COOKIE_NAME)?.value,
      request.headers.get("x-csrf-token"),
    )
  );
}

export function sessionToken(request: NextRequest): string | null {
  return request.cookies.get(SESSION_COOKIE_NAME)?.value?.trim() || null;
}

export async function fetchBackendSession(token: string): Promise<Response> {
  return fetch(`${complianceApiBaseUrl()}/api/v1/auth/session`, {
    method: "GET",
    headers: { Authorization: `Bearer ${token}`, ...bffBackendHeaders() },
    cache: "no-store",
    signal: AbortSignal.timeout(BACKEND_TIMEOUT_MS),
  });
}

export function setSessionCookies(
  response: NextResponse,
  token: string,
  expiresAtUtc: string | undefined,
): void {
  const maxAge = sessionMaxAge(expiresAtUtc);
  response.cookies.set(SESSION_COOKIE_NAME, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "strict",
    path: "/",
    maxAge,
  });
  response.cookies.set(CSRF_COOKIE_NAME, randomBytes(32).toString("base64url"), {
    httpOnly: false,
    secure: process.env.NODE_ENV === "production",
    sameSite: "strict",
    path: "/",
    maxAge,
  });
}

export function clearSessionCookies(response: NextResponse): void {
  const shared = {
    secure: process.env.NODE_ENV === "production",
    sameSite: "strict" as const,
    path: "/",
    maxAge: 0,
  };
  response.cookies.set(SESSION_COOKIE_NAME, "", { ...shared, httpOnly: true });
  response.cookies.set(CSRF_COOKIE_NAME, "", { ...shared, httpOnly: false });
}

export function noStoreJson(
  body: unknown,
  init?: { status?: number },
): NextResponse {
  return NextResponse.json(body, {
    ...init,
    headers: {
      "Cache-Control": "no-store, max-age=0",
      Pragma: "no-cache",
    },
  });
}

function sessionMaxAge(expiresAtUtc: string | undefined): number {
  if (!expiresAtUtc) return DEFAULT_SESSION_MAX_AGE_SECONDS;
  const expiresAt = Date.parse(expiresAtUtc);
  if (!Number.isFinite(expiresAt)) return DEFAULT_SESSION_MAX_AGE_SECONDS;
  const seconds = Math.floor((expiresAt - Date.now()) / 1000);
  return Math.max(1, Math.min(seconds, 24 * 60 * 60));
}
