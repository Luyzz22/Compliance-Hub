import { NextResponse } from "next/server";

import { computeGtmDashboardSnapshot } from "@/lib/gtmDashboardAggregate";
import { isLeadAdminAuthorized } from "@/lib/leadAdminAuth";
import { computeProductBridgePayload } from "@/lib/gtmProductBridgeAggregate";
import { readGtmWeeklyReviewState, sliceRecentNotes } from "@/lib/gtmWeeklyReviewStore";

export const runtime = "nodejs";

export async function GET(req: Request) {
  if (!process.env.LEAD_ADMIN_SECRET?.trim()) {
    return NextResponse.json({ error: "not_configured" }, { status: 404 });
  }
  if (!isLeadAdminAuthorized(req)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const [snapshot, product_bridge] = await Promise.all([
    computeGtmDashboardSnapshot(),
    computeProductBridgePayload(),
  ]);
  const wr = await readGtmWeeklyReviewState();
  const weekly_review = {
    last_reviewed_at: wr.last_reviewed_at,
    recent_notes: sliceRecentNotes(wr, 3),
  };
  return NextResponse.json({ ok: true, snapshot, weekly_review, product_bridge });
}
