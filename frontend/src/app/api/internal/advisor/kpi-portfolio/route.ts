import { NextResponse } from "next/server";

import { computeAdvisorKpiPortfolioSnapshot } from "@/lib/advisorKpiPortfolioAggregate";
import { isLeadAdminAuthorized } from "@/lib/leadAdminAuth";

export const runtime = "nodejs";

export async function GET(req: Request) {
  if (!process.env.LEAD_ADMIN_SECRET?.trim()) {
    return NextResponse.json({ error: "not_configured" }, { status: 404 });
  }
  if (!isLeadAdminAuthorized(req)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const url = new URL(req.url);
  const wRaw = url.searchParams.get("window_days");
  const windowDays = Math.min(365, Math.max(7, Number.parseInt(wRaw ?? "90", 10) || 90));
  const seg = url.searchParams.get("segment_by")?.trim().toLowerCase();
  const segmentBy: "readiness" | "primary_segment" =
    seg === "primary_segment" || seg === "segment" ? "primary_segment" : "readiness";

  const snapshot = await computeAdvisorKpiPortfolioSnapshot(new Date(), windowDays, segmentBy);

  return NextResponse.json({
    ok: true,
    advisor_kpi_portfolio: snapshot,
  });
}
