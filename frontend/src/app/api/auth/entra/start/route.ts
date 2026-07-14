import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { ENTRA_TRANSACTION_COOKIE_NAME } from "@/lib/authConstants";
import { createEntraAuthorization } from "@/lib/entraAuth";

export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  try {
    const { authorizationUrl, sealedTransaction } = await createEntraAuthorization(
      request.nextUrl.searchParams.get("next"),
    );
    const response = NextResponse.redirect(authorizationUrl, 302);
    response.headers.set("Cache-Control", "no-store, max-age=0");
    response.cookies.set(ENTRA_TRANSACTION_COOKIE_NAME, sealedTransaction, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 10 * 60,
    });
    return response;
  } catch {
    return NextResponse.redirect(
      new URL("/auth/login?error=entra_unavailable", request.url),
      302,
    );
  }
}
