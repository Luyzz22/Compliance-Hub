import { NextResponse } from "next/server";

import { attachAdvisorKpiToPayload } from "@/lib/advisorKpiPortfolioAggregate";
import { computeAdvisorAiGovernanceFromBundle } from "@/lib/advisorAiGovernanceAggregate";
import { buildAdvisorEvidenceHooksPortfolioDto } from "@/lib/advisorEvidenceHookBuild";
import { readAdvisorEvidenceHooks } from "@/lib/advisorEvidenceHookStore";
import { buildBoardReadyEvidencePack } from "@/lib/boardReadyEvidencePackBuild";
import { buildCrossRegulationMatrixFromPayload } from "@/lib/advisorCrossRegulationBuild";
import { computeKanzleiPortfolioPayload } from "@/lib/kanzleiPortfolioAggregate";
import { loadMappedTenantPillarSnapshots } from "@/lib/boardReadinessAggregate";
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
  const crossRegulation = buildCrossRegulationMatrixFromPayload(payload);
  const evidenceHooks = buildAdvisorEvidenceHooksPortfolioDto(payload, storedEvidenceHooks);

  const kpiSnapshot = kpiOff ? null : await attachAdvisorKpiToPayload(payload, now.getTime(), kpiWindowDays);

  const board_ready_evidence_pack = buildBoardReadyEvidencePack({
    payload,
    crossRegulation,
    aiGovernance,
    evidenceHooks,
    kpiSnapshot,
    generatedAt: now,
  });

  return NextResponse.json({
    ok: true,
    board_ready_evidence_pack,
    markdown_de: board_ready_evidence_pack.markdown_de,
  });
}
