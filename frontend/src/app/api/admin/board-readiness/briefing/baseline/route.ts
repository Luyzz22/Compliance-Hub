import { NextResponse } from "next/server";

import { computeBoardReadinessPayload } from "@/lib/boardReadinessAggregate";
import { baselineFromPayload } from "@/lib/boardReadinessBriefingGenerate";
import {
  readBoardReadinessBriefingBaseline,
  writeBoardReadinessBriefingBaseline,
} from "@/lib/boardReadinessBriefingSnapshotStore";
import { isLeadAdminAuthorized } from "@/lib/leadAdminAuth";

export const runtime = "nodejs";

/**
 * POST: Speichert eine Baseline für Delta-Hinweise im nächsten Briefing (optional Wave 35).
 */
export async function POST(req: Request) {
  if (!process.env.LEAD_ADMIN_SECRET?.trim()) {
    return NextResponse.json({ error: "not_configured" }, { status: 404 });
  }
  if (!isLeadAdminAuthorized(req)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const payload = await computeBoardReadinessPayload();
  const baseline = baselineFromPayload(payload);
  await writeBoardReadinessBriefingBaseline(baseline);

  const stored = await readBoardReadinessBriefingBaseline();
  return NextResponse.json({
    ok: true,
    baseline: stored,
    message_de: "Baseline für Board-Readiness-Briefing gespeichert.",
  });
}
