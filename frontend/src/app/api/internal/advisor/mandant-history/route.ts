import { NextResponse } from "next/server";

import { getAdvisorMandantHistoryApiDto } from "@/lib/advisorMandantHistoryStore";
import { isLeadAdminAuthorized } from "@/lib/leadAdminAuth";

export const runtime = "nodejs";

const CLIENT_ID_RE = /^[a-zA-Z0-9._-]{1,255}$/;

export async function GET(req: Request) {
  if (!process.env.LEAD_ADMIN_SECRET?.trim()) {
    return NextResponse.json({ error: "not_configured" }, { status: 404 });
  }
  if (!isLeadAdminAuthorized(req)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const url = new URL(req.url);
  const clientId = url.searchParams.get("client_id")?.trim() ?? "";
  if (!clientId || !CLIENT_ID_RE.test(clientId)) {
    return NextResponse.json(
      { error: "invalid_client_id", detail: "client_id required (alphanumeric, dot, underscore, hyphen)." },
      { status: 400 },
    );
  }

  const history = await getAdvisorMandantHistoryApiDto(clientId);
  return NextResponse.json({ ok: true, mandant_history: history });
}
