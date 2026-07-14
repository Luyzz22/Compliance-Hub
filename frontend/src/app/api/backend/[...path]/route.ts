import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import {
  clearSessionCookies,
  complianceApiBaseUrl,
  fetchBackendSession,
  mutationCsrfIsValid,
  noStoreJson,
  sessionToken,
  type PublicSession,
} from "@/lib/serverSession";

export const runtime = "nodejs";

const MAX_REQUEST_BYTES = 25 * 1024 * 1024;
const MUTATING_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);
const FORWARDED_REQUEST_HEADERS = [
  "accept",
  "content-type",
  "idempotency-key",
  "if-match",
] as const;
const FORWARDED_RESPONSE_HEADERS = [
  "content-disposition",
  "content-length",
  "content-type",
  "etag",
  "last-modified",
] as const;

type RouteContext = { params: Promise<{ path: string[] }> };

async function forward(request: NextRequest, context: RouteContext) {
  const token = sessionToken(request);
  if (!token) return noStoreJson({ error: "authentication_required" }, { status: 401 });
  if (MUTATING_METHODS.has(request.method) && !mutationCsrfIsValid(request)) {
    return noStoreJson({ error: "csrf_validation_failed" }, { status: 403 });
  }

  const length = Number(request.headers.get("content-length") || "0");
  if (Number.isFinite(length) && length > MAX_REQUEST_BYTES) {
    return noStoreJson({ error: "request_too_large" }, { status: 413 });
  }

  let principalResponse: Response;
  try {
    principalResponse = await fetchBackendSession(token);
  } catch {
    return noStoreJson({ error: "identity_unavailable" }, { status: 503 });
  }
  if (!principalResponse.ok) {
    const response = noStoreJson({ error: "invalid_session" }, { status: 401 });
    clearSessionCookies(response);
    return response;
  }
  const principal = (await principalResponse.json()) as PublicSession;

  const { path } = await context.params;
  if (!path.length || path[0] !== "api" || path[1] !== "v1") {
    return noStoreJson({ error: "route_not_allowed" }, { status: 404 });
  }
  const safePath = path.map((segment) => encodeURIComponent(segment)).join("/");
  const target = new URL(`/${safePath}`, complianceApiBaseUrl());
  target.search = request.nextUrl.search;

  const headers = new Headers({
    Authorization: `Bearer ${token}`,
    "x-tenant-id": principal.tenant_id,
  });
  for (const name of FORWARDED_REQUEST_HEADERS) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }

  let body: ArrayBuffer | undefined;
  if (request.method !== "GET" && request.method !== "HEAD") {
    body = await request.arrayBuffer();
    if (body.byteLength > MAX_REQUEST_BYTES) {
      return noStoreJson({ error: "request_too_large" }, { status: 413 });
    }
  }

  let backend: Response;
  try {
    backend = await fetch(target, {
      method: request.method,
      headers,
      body,
      cache: "no-store",
      redirect: "manual",
      signal: AbortSignal.timeout(30_000),
    });
  } catch {
    return noStoreJson({ error: "backend_unavailable" }, { status: 503 });
  }

  const responseHeaders = new Headers({
    "Cache-Control": "no-store, max-age=0",
    Pragma: "no-cache",
  });
  for (const name of FORWARDED_RESPONSE_HEADERS) {
    const value = backend.headers.get(name);
    if (value) responseHeaders.set(name, value);
  }
  return new NextResponse(backend.body, {
    status: backend.status,
    headers: responseHeaders,
  });
}

export const GET = forward;
export const POST = forward;
export const PUT = forward;
export const PATCH = forward;
export const DELETE = forward;
