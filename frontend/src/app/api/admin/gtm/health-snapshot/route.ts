import { NextResponse } from "next/server";

import { computeGtmDashboardSnapshot } from "@/lib/gtmDashboardAggregate";
import { buildGtmHealthSnapshotPayload } from "@/lib/gtmHealthSnapshotBuilder";
import { isLeadAdminOrGtmAlertSecretAuthorized, leadAdminOrGtmAlertSecretIsConfigured } from "@/lib/leadAdminAuth";

export const runtime = "nodejs";

export async function GET(req: Request) {
  if (!leadAdminOrGtmAlertSecretIsConfigured()) {
    return NextResponse.json({ error: "not_configured" }, { status: 404 });
  }
  if (!isLeadAdminOrGtmAlertSecretAuthorized(req)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const snapshot = await computeGtmDashboardSnapshot();
  const health_snapshot = buildGtmHealthSnapshotPayload(snapshot);
  return NextResponse.json({ ok: true, health_snapshot });
}
