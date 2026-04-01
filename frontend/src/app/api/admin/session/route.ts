import { NextResponse } from "next/server";

import {
  createLeadAdminSessionToken,
  isLeadAdminAuthorized,
  LEAD_ADMIN_COOKIE_NAME,
  leadAdminCookieOptions,
} from "@/lib/leadAdminAuth";

export const runtime = "nodejs";

/** Setzt Session-Cookie nach erfolgreicher Secret-Prüfung (internes Lead-Inbox-UI). */
export async function POST(req: Request) {
  const secret = process.env.LEAD_ADMIN_SECRET?.trim();
  if (!secret) {
    return NextResponse.json({ ok: false, error: "not_configured" }, { status: 404 });
  }

  let body: { secret?: string } = {};
  try {
    body = (await req.json()) as { secret?: string };
  } catch {
    return NextResponse.json({ ok: false, error: "invalid_json" }, { status: 400 });
  }

  const provided = typeof body.secret === "string" ? body.secret.trim() : "";
  if (!provided || provided !== secret) {
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
  if (!process.env.LEAD_ADMIN_SECRET?.trim()) {
    return NextResponse.json({ ok: false, error: "not_configured" }, { status: 404 });
  }
  if (!isLeadAdminAuthorized(req)) {
    return NextResponse.json({ ok: false, error: "unauthorized" }, { status: 401 });
  }
  const res = NextResponse.json({ ok: true });
  res.cookies.set(LEAD_ADMIN_COOKIE_NAME, "", { ...leadAdminCookieOptions(), maxAge: 0 });
  return res;
}
