import { createHash } from "node:crypto";

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import {
  bffBackendHeaders,
  complianceApiBaseUrl,
  mutationRequestIsTrusted,
  noStoreJson,
} from "@/lib/serverSession";
import { isEnterpriseProductionRuntime } from "@/lib/outboundEndpointPolicy";

const MAX_REQUEST_BYTES = 16 * 1024;
const WINDOW_MS = 15 * 60 * 1000;
const buckets = new Map<string, { count: number; resetAt: number }>();

const operations = {
  register: { path: "/api/v1/auth/register", maximum: 5 },
  password_reset_request: {
    path: "/api/v1/auth/password-reset/request",
    maximum: 5,
  },
  password_reset_confirm: {
    path: "/api/v1/auth/password-reset/confirm",
    maximum: 10,
  },
} as const;

export type PublicIdentityOperation = keyof typeof operations;

function clientNetworkKey(request: NextRequest): string {
  const forwarded = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim();
  const address = forwarded || request.headers.get("x-real-ip")?.trim() || "unknown";
  return createHash("sha256").update(address.slice(0, 128)).digest("hex").slice(0, 32);
}

function rateLimit(operation: PublicIdentityOperation, request: NextRequest) {
  const now = Date.now();
  const key = `${operation}:${clientNetworkKey(request)}`;
  let bucket = buckets.get(key);
  if (!bucket || now >= bucket.resetAt) {
    bucket = { count: 0, resetAt: now + WINDOW_MS };
    buckets.set(key, bucket);
  }
  if (bucket.count >= operations[operation].maximum) {
    return { allowed: false as const, retryAfter: Math.ceil((bucket.resetAt - now) / 1000) };
  }
  bucket.count += 1;
  if (buckets.size > 5_000) {
    for (const [bucketKey, candidate] of buckets) {
      if (now >= candidate.resetAt) buckets.delete(bucketKey);
    }
  }
  return { allowed: true as const };
}

export async function proxyPublicIdentityMutation(
  request: NextRequest,
  operation: PublicIdentityOperation,
): Promise<NextResponse> {
  if (isEnterpriseProductionRuntime()) {
    return noStoreJson({ error: "local_identity_disabled" }, { status: 404 });
  }
  if (!mutationRequestIsTrusted(request)) {
    return noStoreJson({ error: "invalid_origin" }, { status: 403 });
  }
  if (!request.headers.get("content-type")?.toLowerCase().startsWith("application/json")) {
    return noStoreJson({ error: "unsupported_media_type" }, { status: 415 });
  }
  const declaredLength = Number(request.headers.get("content-length") || "0");
  if (Number.isFinite(declaredLength) && declaredLength > MAX_REQUEST_BYTES) {
    return noStoreJson({ error: "request_too_large" }, { status: 413 });
  }

  const limit = rateLimit(operation, request);
  if (!limit.allowed) {
    return NextResponse.json(
      { error: "rate_limited", retry_after_seconds: limit.retryAfter },
      {
        status: 429,
        headers: {
          "Cache-Control": "no-store, max-age=0",
          "Retry-After": String(limit.retryAfter),
        },
      },
    );
  }

  const rawBody = await request.text();
  if (!rawBody || Buffer.byteLength(rawBody, "utf8") > MAX_REQUEST_BYTES) {
    return noStoreJson({ error: "invalid_request" }, { status: 400 });
  }
  try {
    const parsed = JSON.parse(rawBody) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return noStoreJson({ error: "invalid_request" }, { status: 400 });
    }
  } catch {
    return noStoreJson({ error: "invalid_request" }, { status: 400 });
  }

  let backend: Response;
  try {
    backend = await fetch(`${complianceApiBaseUrl()}${operations[operation].path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...bffBackendHeaders() },
      body: rawBody,
      cache: "no-store",
      redirect: "manual",
      signal: AbortSignal.timeout(10_000),
    });
  } catch {
    return noStoreJson({ error: "identity_unavailable" }, { status: 503 });
  }

  if (backend.status >= 500) {
    return noStoreJson({ error: "identity_unavailable" }, { status: 503 });
  }
  const responseBody = await backend.text();
  return new NextResponse(responseBody, {
    status: backend.status,
    headers: {
      "Cache-Control": "no-store, max-age=0",
      "Content-Type": "application/json",
      Pragma: "no-cache",
    },
  });
}
