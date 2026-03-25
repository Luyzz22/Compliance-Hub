import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import {
  DEMO_MODE_SESSION_COOKIE,
  WORKSPACE_TENANT_COOKIE,
} from "@/lib/workspaceTenantConstants";

export function middleware(request: NextRequest) {
  const res = NextResponse.next();
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
        maxAge: 60 * 60 * 24 * 90,
        sameSite: "lax",
      });
    }
  }
  return res;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
};
