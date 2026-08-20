import { NextResponse } from "next/server";

import {
  InvalidJsonBodyError,
  readBoundedJsonBody,
  RequestBodyTooLargeError,
} from "@/lib/boundedJsonBody";
import {
  createLeadAdminSessionToken,
  isLeadAdminAuthorized,
  LEAD_ADMIN_COOKIE_NAME,
  leadAdminCredentialIsValid,
  leadAdminIsConfigured,
  leadAdminCookieOptions,
} from "@/lib/leadAdminAuth";

export const runtime = "nodejs";

const MAX_REQUEST_BYTES = 16 * 1024;

/** Setzt Session-Cookie nach erfolgreicher Secret-Prüfung (internes Lead-Inbox-UI). */
export async function POST(req: Request) {
  if (!leadAdminIsConfigured()) {
    return NextResponse.json({ ok: false, error: "not_configured" }, { status: 404 });
  }

  let body: { secret?: string } = {};
  try {
    body = await readBoundedJsonBody<{ secret?: string }>(req, MAX_REQUEST_BYTES);
  } catch (error) {
    if (error instanceof RequestBodyTooLargeError) {
      return NextResponse.json({ ok: false, error: "request_too_large" }, { status: 413 });
    }
    if (!(error instanceof InvalidJsonBodyError)) throw error;
    return NextResponse.json({ ok: false, error: "invalid_json" }, { status: 400 });
  }

  const provided = typeof body.secret === "string" ? body.secret.trim() : "";
  if (!leadAdminCredentialIsValid(provided)) {
    return NextResponse.json({ ok: false, error: "unauthorized" }, { status: 401 });
  }

  const token = createLeadAdminSessionToken();
  if (!token) {
    return NextResponse.json({ ok: false, error: "server" }, { status: 500 });
  }

  const res = NextResponse.json({ ok: true });
  res.cookies.set(LEAD_ADMIN_COOKIE_NAME, token, leadAdminCookieOptions());
  return res;
}

export async function DELETE(req: Request) {
  if (!leadAdminIsConfigured()) {
    return NextResponse.json({ ok: false, error: "not_configured" }, { status: 404 });
  }
  if (!isLeadAdminAuthorized(req)) {
    return NextResponse.json({ ok: false, error: "unauthorized" }, { status: 401 });
  }
  const res = NextResponse.json({ ok: true });
  res.cookies.set(LEAD_ADMIN_COOKIE_NAME, "", { ...leadAdminCookieOptions(), maxAge: 0 });
  return res;
}
