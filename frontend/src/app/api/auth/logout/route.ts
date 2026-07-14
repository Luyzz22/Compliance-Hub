import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import {
  bffBackendHeaders,
  clearSessionCookies,
  complianceApiBaseUrl,
  mutationCsrfIsValid,
  noStoreJson,
  sessionToken,
} from "@/lib/serverSession";

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  if (!mutationCsrfIsValid(request)) {
    return noStoreJson({ ok: false, error: "csrf_validation_failed" }, { status: 403 });
  }

  const token = sessionToken(request);
  if (token) {
    try {
      await fetch(`${complianceApiBaseUrl()}/api/v1/auth/session`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}`, ...bffBackendHeaders() },
        cache: "no-store",
        signal: AbortSignal.timeout(10_000),
      });
    } catch {
      // Local session invalidation remains fail-closed when the identity service is unavailable.
    }
  }

  const response = new NextResponse(null, {
    status: 204,
    headers: { "Cache-Control": "no-store, max-age=0" },
  });
  clearSessionCookies(response);
  return response;
}
