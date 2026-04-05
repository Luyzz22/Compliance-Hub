import { NextResponse } from "next/server";

import { computeKanzleiPortfolioPayload } from "@/lib/kanzleiPortfolioAggregate";
import { isLeadAdminAuthorized } from "@/lib/leadAdminAuth";

export const runtime = "nodejs";

export async function GET(req: Request) {
  if (!process.env.LEAD_ADMIN_SECRET?.trim()) {
    return NextResponse.json({ error: "not_configured" }, { status: 404 });
  }
  if (!isLeadAdminAuthorized(req)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const payload = await computeKanzleiPortfolioPayload(new Date());

  return NextResponse.json({
    ok: true,
    advisor_sla: payload.advisor_sla,
    portfolio_generated_at: payload.generated_at,
  });
}
