import { NextResponse } from "next/server";

import { computeAdvisorAiGovernanceOverview } from "@/lib/advisorAiGovernanceAggregate";
import { isLeadAdminAuthorized } from "@/lib/leadAdminAuth";

export const runtime = "nodejs";

export async function GET(req: Request) {
  if (!process.env.LEAD_ADMIN_SECRET?.trim()) {
    return NextResponse.json({ error: "not_configured" }, { status: 404 });
  }
  if (!isLeadAdminAuthorized(req)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const overview = await computeAdvisorAiGovernanceOverview(new Date());
  return NextResponse.json({
    ok: true,
    ai_governance_overview: overview,
    markdown_de: overview.markdown_de,
  });
}
