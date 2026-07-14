import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { ENTRA_TRANSACTION_COOKIE_NAME } from "@/lib/authConstants";
import {
  entraConfig,
  redeemEntraAuthorizationCode,
} from "@/lib/entraAuth";
import {
  openEntraTransaction,
  secureValuesEqual,
} from "@/lib/entraTransaction";
import {
  bffBackendHeaders,
  complianceApiBaseUrl,
  setSessionCookies,
} from "@/lib/serverSession";

export const runtime = "nodejs";

type BackendLogin = {
  session_token?: string;
  expires_at_utc?: string;
};

function clearTransactionCookie(response: NextResponse): void {
  response.cookies.set(ENTRA_TRANSACTION_COOKIE_NAME, "", {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 0,
  });
}

function loginError(request: NextRequest, code: string): NextResponse {
  const response = NextResponse.redirect(
    new URL(`/auth/login?error=${encodeURIComponent(code)}`, request.url),
    302,
  );
  response.headers.set("Cache-Control", "no-store, max-age=0");
  clearTransactionCookie(response);
  return response;
}

export async function GET(request: NextRequest) {
  if (request.nextUrl.searchParams.has("error")) {
    return loginError(request, "entra_authorization_denied");
  }
  const code = request.nextUrl.searchParams.get("code") || "";
  const state = request.nextUrl.searchParams.get("state") || "";
  const sealed = request.cookies.get(ENTRA_TRANSACTION_COOKIE_NAME)?.value || "";

  try {
    const config = entraConfig();
    const transaction = openEntraTransaction(sealed, config.transactionSecret);
    if (!transaction || !secureValuesEqual(state, transaction.state)) {
      return loginError(request, "entra_transaction_invalid");
    }
    if (code.length < 20 || code.length > 8192) {
      return loginError(request, "entra_transaction_invalid");
    }

    const identity = await redeemEntraAuthorizationCode(code, transaction);
    const backend = await fetch(`${complianceApiBaseUrl()}/api/v1/auth/session/entra`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...bffBackendHeaders() },
      body: JSON.stringify({
        provider_id: transaction.providerId,
        id_token: identity.idToken,
        expected_nonce: transaction.nonce,
      }),
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
    const payload = (await backend.json().catch(() => null)) as BackendLogin | null;
    if (!backend.ok || !payload?.session_token) {
      return loginError(request, "entra_access_denied");
    }

    const response = NextResponse.redirect(
      new URL(transaction.returnTo, config.appOrigin),
      303,
    );
    response.headers.set("Cache-Control", "no-store, max-age=0");
    setSessionCookies(response, payload.session_token, payload.expires_at_utc);
    clearTransactionCookie(response);
    return response;
  } catch {
    return loginError(request, "entra_login_failed");
  }
}
