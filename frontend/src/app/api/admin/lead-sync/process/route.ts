import { NextResponse } from "next/server";

import { isLeadAdminAuthorized } from "@/lib/leadAdminAuth";
import { processPendingLeadSyncJobs } from "@/lib/leadSyncDispatcher";

export const runtime = "nodejs";

/** Warteschlange abarbeiten (Cron oder manuell). */
export async function POST(req: Request) {
  if (!process.env.LEAD_ADMIN_SECRET?.trim()) {
    return NextResponse.json({ error: "not_configured" }, { status: 404 });
  }
  if (!isLeadAdminAuthorized(req)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  let limit = 25;
  try {
    const body = (await req.json()) as { limit?: number };
    if (typeof body.limit === "number" && Number.isFinite(body.limit)) {
      limit = Math.min(200, Math.max(1, Math.floor(body.limit)));
    }
  } catch {
    /* empty body ok */
  }

  const processed = await processPendingLeadSyncJobs(limit);
  return NextResponse.json({ ok: true, processed });
}
