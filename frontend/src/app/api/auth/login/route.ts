import type { NextRequest } from "next/server";

import { parseLoginBody } from "@/lib/sessionSecurity";
import {
  bffBackendHeaders,
  complianceApiBaseUrl,
  mutationRequestIsTrusted,
  noStoreJson,
  setSessionCookies,
} from "@/lib/serverSession";

export const runtime = "nodejs";

type BackendLogin = {
  session_token?: string;
  expires_at_utc?: string;
  user_id?: string;
  email?: string;
  display_name?: string | null;
  tenant_id?: string;
  role?: string;
};

export async function POST(request: NextRequest) {
  if (!mutationRequestIsTrusted(request)) {
    return noStoreJson({ ok: false, error: "invalid_origin" }, { status: 403 });
  }

  const body = parseLoginBody(await request.text());
  if (!body) {
    return noStoreJson({ ok: false, error: "invalid_request" }, { status: 400 });
  }

  let backend: Response;
  try {
    backend = await fetch(`${complianceApiBaseUrl()}/api/v1/auth/session/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...bffBackendHeaders() },
      body: JSON.stringify(body),
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
  } catch {
    return noStoreJson({ ok: false, error: "identity_unavailable" }, { status: 503 });
  }

  const payload = (await backend.json().catch(() => null)) as BackendLogin | null;
  if (!backend.ok || !payload?.session_token) {
    const detail =
      payload && "detail" in payload
        ? (payload as { detail?: unknown }).detail
        : undefined;
    return noStoreJson(
      { ok: false, error: "login_failed", detail },
      { status: backend.status >= 400 && backend.status < 500 ? backend.status : 503 },
    );
  }

  const response = noStoreJson({
    ok: true,
    user: {
      user_id: payload.user_id,
      email: payload.email,
      display_name: payload.display_name,
      tenant_id: payload.tenant_id,
      role: payload.role,
    },
  });
  setSessionCookies(response, payload.session_token, payload.expires_at_utc);
  return response;
}
