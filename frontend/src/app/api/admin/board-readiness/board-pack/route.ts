import { NextResponse } from "next/server";

import { computeBoardReadinessPayload } from "@/lib/boardReadinessAggregate";
import { generateQuarterlyBoardPack } from "@/lib/boardPackGenerate";
import { readBoardReadinessBriefingBaseline } from "@/lib/boardReadinessBriefingSnapshotStore";
import { isLeadAdminAuthorized } from "@/lib/leadAdminAuth";

export const runtime = "nodejs";

export async function GET(_req: Request) {
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
  const board_pack = generateQuarterlyBoardPack(payload, baseline);

  return NextResponse.json({ ok: true, board_pack });
}
