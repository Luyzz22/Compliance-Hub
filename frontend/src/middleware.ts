import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import {
  DEMO_MODE_SESSION_COOKIE,
  WORKSPACE_TENANT_COOKIE,
} from "@/lib/workspaceTenantConstants";

const WORKSPACE_COOKIE_MAX_AGE_SEC = 90 * 24 * 60 * 60;

function safeDecodeWorkspaceCookie(raw: string): string {
  const t = raw.trim();
  if (!t) {
    return "";
  }
  try {
    return decodeURIComponent(t);
  } catch {
    return t;
  }
}

/** Align `/tenants/:id/...` with `ch_workspace_tenant` so UI + API use one mandant. */
function applyTenantsWorkspaceCookiePolicy(request: NextRequest, res: NextResponse): NextResponse | null {
  const { pathname } = request.nextUrl;
  const m = pathname.match(/^\/tenants\/([^/]+)(\/.*)?$/);
  if (!m) {
    return null;
  }
  let urlTenant: string;
  try {
    urlTenant = decodeURIComponent(m[1]);
  } catch {
    urlTenant = m[1];
  }
  const suffix = m[2] ?? "";
  const cookieRaw = request.cookies.get(WORKSPACE_TENANT_COOKIE)?.value;
  const workspace = cookieRaw ? safeDecodeWorkspaceCookie(cookieRaw) : "";

  if (workspace && workspace !== urlTenant) {
    const dest = request.nextUrl.clone();
    dest.pathname = `/tenants/${encodeURIComponent(workspace)}${suffix}`;
    return NextResponse.redirect(dest);
  }
  if (!workspace) {
    res.cookies.set(WORKSPACE_TENANT_COOKIE, encodeURIComponent(urlTenant), {
      path: "/",
      maxAge: WORKSPACE_COOKIE_MAX_AGE_SEC,
      sameSite: "lax",
    });
  }
  return null;
}

export function middleware(request: NextRequest) {
  const res = NextResponse.next();
  const tenantsRedirect = applyTenantsWorkspaceCookiePolicy(request, res);
  if (tenantsRedirect) {
    return tenantsRedirect;
  }
  const demo = request.nextUrl.searchParams.get("demo");
  if (demo === "1") {
    res.cookies.set(DEMO_MODE_SESSION_COOKIE, "1", {
      path: "/",
      maxAge: 60 * 60 * 24 * 14,
      sameSite: "lax",
    });
    const tid = process.env.NEXT_PUBLIC_DEMO_WORKSPACE_TENANT_ID?.trim();
    if (tid) {
      res.cookies.set(WORKSPACE_TENANT_COOKIE, encodeURIComponent(tid), {
        path: "/",
        maxAge: WORKSPACE_COOKIE_MAX_AGE_SEC,
        sameSite: "lax",
      });
    }
  }
  return res;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
};
