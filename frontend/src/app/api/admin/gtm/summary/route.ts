import { NextResponse } from "next/server";

import { computeGtmDashboardSnapshot } from "@/lib/gtmDashboardAggregate";
import { isLeadAdminAuthorized } from "@/lib/leadAdminAuth";

export const runtime = "nodejs";

export async function GET(req: Request) {
  if (!process.env.LEAD_ADMIN_SECRET?.trim()) {
    return NextResponse.json({ error: "not_configured" }, { status: 404 });
  }
  if (!isLeadAdminAuthorized(req)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const snapshot = await computeGtmDashboardSnapshot();
  return NextResponse.json({ ok: true, snapshot });
}
