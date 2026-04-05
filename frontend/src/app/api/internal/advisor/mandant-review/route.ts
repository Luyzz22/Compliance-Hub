import { NextResponse } from "next/server";

import { getAdvisorMandantHistoryApiDto, recordAdvisorReviewMarked } from "@/lib/advisorMandantHistoryStore";
import { isLeadAdminAuthorized } from "@/lib/leadAdminAuth";

export const runtime = "nodejs";

const CLIENT_ID_RE = /^[a-zA-Z0-9._-]{1,255}$/;

type Body = {
  client_id?: string;
  note_de?: string;
};

export async function POST(req: Request) {
  if (!process.env.LEAD_ADMIN_SECRET?.trim()) {
    return NextResponse.json({ error: "not_configured" }, { status: 404 });
  }
  if (!isLeadAdminAuthorized(req)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  let body: Body = {};
  try {
    body = (await req.json()) as Body;
  } catch {
    return NextResponse.json({ error: "invalid_json" }, { status: 400 });
  }

  const clientId = typeof body.client_id === "string" ? body.client_id.trim() : "";
  if (!clientId || !CLIENT_ID_RE.test(clientId)) {
    return NextResponse.json(
      { error: "invalid_client_id", detail: "client_id required (alphanumeric, dot, underscore, hyphen)." },
      { status: 400 },
    );
  }

  const noteDe =
    body.note_de === undefined
      ? undefined
      : body.note_de === null
        ? ""
        : String(body.note_de);

  await recordAdvisorReviewMarked(clientId, noteDe);
  const history = await getAdvisorMandantHistoryApiDto(clientId);

  return NextResponse.json({ ok: true, mandant_history: history });
}
