import { NextResponse } from "next/server";

import { computeBoardReadinessPayload } from "@/lib/boardReadinessAggregate";
import { generateBoardReadinessBriefing } from "@/lib/boardReadinessBriefingGenerate";
import { readBoardReadinessBriefingBaseline } from "@/lib/boardReadinessBriefingSnapshotStore";
import { isLeadAdminAuthorized } from "@/lib/leadAdminAuth";

export const runtime = "nodejs";

export async function GET(req: Request) {
  if (!process.env.LEAD_ADMIN_SECRET?.trim()) {
    return NextResponse.json({ error: "not_configured" }, { status: 404 });
  }
  if (!isLeadAdminAuthorized(req)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const [payload, baseline] = await Promise.all([
    computeBoardReadinessPayload(),
    readBoardReadinessBriefingBaseline(),
  ]);
  const briefing = generateBoardReadinessBriefing(payload, baseline);

  return NextResponse.json({ ok: true, briefing });
}
