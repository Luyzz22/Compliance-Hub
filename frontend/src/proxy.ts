import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import {
  isProtectedAppPath,
  SESSION_COOKIE_NAME,
} from "@/lib/authConstants";
import {
  DEMO_MODE_SESSION_COOKIE,
  WORKSPACE_TENANT_COOKIE,
} from "@/lib/workspaceTenantConstants";
import {
  buildContentSecurityPolicy,
  CSP_REPORT_ENDPOINT,
  CSP_REPORTING_GROUP,
  createCspNonce,
} from "@/lib/contentSecurityPolicy";

const WORKSPACE_COOKIE_MAX_AGE_SEC = 90 * 24 * 60 * 60;

function applyRequestSecurityPolicy(
  response: NextResponse,
  contentSecurityPolicy: string,
): NextResponse {
  response.headers.set("Content-Security-Policy", contentSecurityPolicy);
  if (contentSecurityPolicy.includes(`report-to ${CSP_REPORTING_GROUP}`)) {
    response.headers.set(
      "Reporting-Endpoints",
      `${CSP_REPORTING_GROUP}=\"${CSP_REPORT_ENDPOINT}\"`,
    );
  }
  response.headers.set("Cache-Control", "private, no-store");
  return response;
}

function safeDecodeWorkspaceCookie(raw: string): string {
  const value = raw.trim();
  if (!value) return "";
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

/** Align `/tenants/:id/...` with `ch_workspace_tenant` so UI and API use one tenant. */
function applyTenantsWorkspaceCookiePolicy(
  request: NextRequest,
  response: NextResponse,
): NextResponse | null {
  const { pathname } = request.nextUrl;
  const match = pathname.match(/^\/tenants\/([^/]+)(\/.*)?$/);
  if (!match) return null;

  let urlTenant: string;
  try {
    urlTenant = decodeURIComponent(match[1]);
  } catch {
    urlTenant = match[1];
  }
  const suffix = match[2] ?? "";
  const cookieRaw = request.cookies.get(WORKSPACE_TENANT_COOKIE)?.value;
  const workspace = cookieRaw ? safeDecodeWorkspaceCookie(cookieRaw) : "";

  if (workspace && workspace !== urlTenant) {
    const destination = request.nextUrl.clone();
    destination.pathname = `/tenants/${encodeURIComponent(workspace)}${suffix}`;
    return NextResponse.redirect(destination);
  }
  if (!workspace) {
    response.cookies.set(WORKSPACE_TENANT_COOKIE, encodeURIComponent(urlTenant), {
      path: "/",
      maxAge: WORKSPACE_COOKIE_MAX_AGE_SEC,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
    });
  }
  return null;
}

export function proxy(request: NextRequest) {
  const nonce = createCspNonce();
  const contentSecurityPolicy = buildContentSecurityPolicy({
    nonce,
    development: process.env.NODE_ENV !== "production",
    apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL,
  });
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("Content-Security-Policy", contentSecurityPolicy);
  const response = NextResponse.next({ request: { headers: requestHeaders } });
  const tenantsRedirect = applyTenantsWorkspaceCookiePolicy(request, response);
  if (tenantsRedirect) {
    return applyRequestSecurityPolicy(tenantsRedirect, contentSecurityPolicy);
  }

  const publicDemoEnabled = process.env.COMPLIANCEHUB_PUBLIC_DEMO_ENABLED === "true";
  const requestedDemo =
    publicDemoEnabled && request.nextUrl.searchParams.get("demo") === "1";
  const existingDemo =
    publicDemoEnabled &&
    request.cookies.get(DEMO_MODE_SESSION_COOKIE)?.value === "1";

  if (requestedDemo) {
    response.cookies.set(DEMO_MODE_SESSION_COOKIE, "1", {
      path: "/",
      maxAge: 60 * 60 * 24 * 14,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
      httpOnly: true,
    });
    const tenantId = process.env.NEXT_PUBLIC_DEMO_WORKSPACE_TENANT_ID?.trim();
    if (tenantId) {
      response.cookies.set(WORKSPACE_TENANT_COOKIE, encodeURIComponent(tenantId), {
        path: "/",
        maxAge: WORKSPACE_COOKIE_MAX_AGE_SEC,
        sameSite: "lax",
        secure: process.env.NODE_ENV === "production",
      });
    }
  }

  const hasSession = Boolean(request.cookies.get(SESSION_COOKIE_NAME)?.value);
  if (
    isProtectedAppPath(request.nextUrl.pathname) &&
    !hasSession &&
    !requestedDemo &&
    !existingDemo
  ) {
    const destination = request.nextUrl.clone();
    const returnTo = `${request.nextUrl.pathname}${request.nextUrl.search}`;
    destination.pathname = "/auth/login";
    destination.search = "";
    destination.searchParams.set("next", returnTo);
    return applyRequestSecurityPolicy(
      NextResponse.redirect(destination),
      contentSecurityPolicy,
    );
  }

  return applyRequestSecurityPolicy(response, contentSecurityPolicy);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
};
