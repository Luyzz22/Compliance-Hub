import { NextResponse } from "next/server";

import { buildCrossRegulationMatrixFromPayload } from "@/lib/advisorCrossRegulationBuild";
import { computeKanzleiPortfolioPayload } from "@/lib/kanzleiPortfolioAggregate";
import { isLeadAdminAuthorized, leadAdminIsConfigured } from "@/lib/leadAdminAuth";

export const runtime = "nodejs";

export async function GET(req: Request) {
  if (!leadAdminIsConfigured()) {
    return NextResponse.json({ error: "not_configured" }, { status: 404 });
  }
  if (!isLeadAdminAuthorized(req)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const payload = await computeKanzleiPortfolioPayload(new Date());
  const cross_regulation_matrix = buildCrossRegulationMatrixFromPayload(payload);
  return NextResponse.json({
    ok: true,
    cross_regulation_matrix,
    markdown_de: cross_regulation_matrix.markdown_de,
  });
}
