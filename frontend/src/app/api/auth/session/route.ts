import type { NextRequest } from "next/server";

import {
  clearSessionCookies,
  fetchBackendSession,
  noStoreJson,
  sessionToken,
} from "@/lib/serverSession";

export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  const token = sessionToken(request);
  if (!token) return noStoreJson({ authenticated: false }, { status: 401 });

  let backend: Response;
  try {
    backend = await fetchBackendSession(token);
  } catch {
    return noStoreJson({ authenticated: false, error: "identity_unavailable" }, { status: 503 });
  }

  if (!backend.ok) {
    const response = noStoreJson({ authenticated: false }, { status: 401 });
    clearSessionCookies(response);
    return response;
  }
  const session = await backend.json();
  return noStoreJson({ authenticated: true, session });
}
