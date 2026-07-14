import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import {
  DEMO_MODE_SESSION_COOKIE,
  WORKSPACE_TENANT_COOKIE,
} from "@/lib/workspaceTenantConstants";

const WORKSPACE_COOKIE_MAX_AGE_SEC = 90 * 24 * 60 * 60;

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
  const response = NextResponse.next();
  const tenantsRedirect = applyTenantsWorkspaceCookiePolicy(request, response);
  if (tenantsRedirect) return tenantsRedirect;

  if (request.nextUrl.searchParams.get("demo") === "1") {
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
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
};
