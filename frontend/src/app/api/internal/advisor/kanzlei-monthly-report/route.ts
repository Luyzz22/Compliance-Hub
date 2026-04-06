import { NextResponse } from "next/server";

import { upsertAdvisorKpiHistoryDaily } from "@/lib/advisorKpiHistoryStore";
import { attachAdvisorKpiToPayload } from "@/lib/advisorKpiPortfolioAggregate";
import { advisorKpiTrendsNarrativeBlock, buildAdvisorKpiTrendsDto } from "@/lib/advisorKpiTrendsBuild";
import { computeAdvisorAiGovernanceFromBundle } from "@/lib/advisorAiGovernanceAggregate";
import { buildAdvisorEvidenceHooksPortfolioDto } from "@/lib/advisorEvidenceHookBuild";
import { readAdvisorEvidenceHooks } from "@/lib/advisorEvidenceHookStore";
import { computeKanzleiPortfolioPayload } from "@/lib/kanzleiPortfolioAggregate";
import { loadMappedTenantPillarSnapshots } from "@/lib/boardReadinessAggregate";
import { readKanzleiMonthlyReportBaseline, writeKanzleiMonthlyReportBaseline } from "@/lib/kanzleiMonthlyReportBaseline";
import { buildKanzleiMonthlyReport } from "@/lib/kanzleiMonthlyReportBuild";
import { kanzleiMonthlyReportMarkdownDe } from "@/lib/kanzleiMonthlyReportMarkdown";
import { isLeadAdminAuthorized } from "@/lib/leadAdminAuth";

export const runtime = "nodejs";

function defaultPeriodLabel(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  return `${y}-${m}`;
}

export async function GET(req: Request) {
  if (!process.env.LEAD_ADMIN_SECRET?.trim()) {
    return NextResponse.json({ error: "not_configured" }, { status: 404 });
  }
  if (!isLeadAdminAuthorized(req)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const url = new URL(req.url);
  const period = url.searchParams.get("period")?.trim() || defaultPeriodLabel();
  const compare = url.searchParams.get("compare") !== "0";
  const updateBaseline = url.searchParams.get("update_baseline") === "1";
  const topNRaw = url.searchParams.get("top_n");
  const attentionTopN = Math.min(25, Math.max(3, Number.parseInt(topNRaw ?? "10", 10) || 10));
  const kpiWindowRaw = url.searchParams.get("kpi_window_days");
  const kpiWindowDays = Math.min(365, Math.max(7, Number.parseInt(kpiWindowRaw ?? "90", 10) || 90));
  const kpiOff = url.searchParams.get("kpi") === "0";

  const now = new Date();
  const bundle = await loadMappedTenantPillarSnapshots(now);
  const [payload, aiGovernance, storedEvidenceHooks] = await Promise.all([
    computeKanzleiPortfolioPayload(now, { preloadedBundle: bundle }),
    Promise.resolve(computeAdvisorAiGovernanceFromBundle(bundle)),
    readAdvisorEvidenceHooks(),
  ]);
  const evidenceHooks = buildAdvisorEvidenceHooksPortfolioDto(payload, storedEvidenceHooks);
  const baseline = await readKanzleiMonthlyReportBaseline();

  const advisorKpiSnapshot = kpiOff
    ? null
    : await attachAdvisorKpiToPayload(payload, now.getTime(), kpiWindowDays);

  let kpiTrendsNarrative = null;
  if (!kpiOff && advisorKpiSnapshot) {
    const hist = await upsertAdvisorKpiHistoryDaily(payload, advisorKpiSnapshot);
    const trends = buildAdvisorKpiTrendsDto({
      history: hist.snapshots,
      period: "3m",
      nowMs: now.getTime(),
    });
    kpiTrendsNarrative = advisorKpiTrendsNarrativeBlock(trends);
  }

  const report = buildKanzleiMonthlyReport(payload, baseline, {
    periodLabel: period,
    compareToBaseline: compare,
    attentionTopN,
    advisorKpiSnapshot,
    kpiTrendsNarrative,
    aiGovernance,
    evidenceHooks,
  });
  const markdown_de = kanzleiMonthlyReportMarkdownDe(report);

  if (updateBaseline) {
    await writeKanzleiMonthlyReportBaseline(payload, period);
  }

  return NextResponse.json({
    ok: true,
    report,
    markdown_de,
    baseline_updated: updateBaseline,
  });
}
