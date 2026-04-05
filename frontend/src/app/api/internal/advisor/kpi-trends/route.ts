import { NextResponse } from "next/server";

import { computeAdvisorKpiPortfolioSnapshot } from "@/lib/advisorKpiPortfolioAggregate";
import { readAdvisorKpiHistoryState } from "@/lib/advisorKpiHistoryStore";
import type { AdvisorKpiTrendPeriod } from "@/lib/advisorKpiTrendsBuild";
import { buildAdvisorKpiTrendsDto } from "@/lib/advisorKpiTrendsBuild";
import { isLeadAdminAuthorized } from "@/lib/leadAdminAuth";

export const runtime = "nodejs";

function parsePeriod(raw: string | null): AdvisorKpiTrendPeriod {
  const p = raw?.trim().toLowerCase();
  if (p === "3m" || p === "quarter" || p === "3mo") return "3m";
  if (p === "qtd" || p === "quarter_to_date") return "qtd";
  return "4w";
}

export async function GET(req: Request) {
  if (!process.env.LEAD_ADMIN_SECRET?.trim()) {
    return NextResponse.json({ error: "not_configured" }, { status: 404 });
  }
  if (!isLeadAdminAuthorized(req)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const url = new URL(req.url);
  const period = parsePeriod(url.searchParams.get("period"));
  const append = url.searchParams.get("append") !== "0";
  const kpiWindowRaw = url.searchParams.get("kpi_window_days");
  const kpiWindowDays = Math.min(365, Math.max(7, Number.parseInt(kpiWindowRaw ?? "90", 10) || 90));
  const segment = url.searchParams.get("segment")?.trim() ?? null;
  const seg = url.searchParams.get("segment_by")?.trim().toLowerCase();
  const segmentBy: "readiness" | "primary_segment" =
    seg === "primary_segment" || seg === "segment" ? "primary_segment" : "readiness";

  const now = new Date();
  const nowMs = now.getTime();

  let history = await readAdvisorKpiHistoryState();
  if (append) {
    await computeAdvisorKpiPortfolioSnapshot(now, kpiWindowDays, segmentBy, { persistHistory: true });
    history = await readAdvisorKpiHistoryState();
  }

  const trends = buildAdvisorKpiTrendsDto({
    history: history.snapshots,
    period,
    nowMs,
    segment_filter: segment,
  });

  return NextResponse.json({
    ok: true,
    advisor_kpi_trends: trends,
    history_snapshot_count: history.snapshots.length,
  });
}
