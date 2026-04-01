import { NextResponse } from "next/server";

import { isLeadAdminAuthorized } from "@/lib/leadAdminAuth";
import { mergeLeadsWithOps, sortInboxItems } from "@/lib/leadInboxMerge";
import type { LeadForwardingStatus } from "@/lib/leadInboxTypes";
import { readLeadOpsState } from "@/lib/leadOpsState";
import { readRecentLeadRecordsMerged } from "@/lib/leadPersistence";

export const runtime = "nodejs";

function isForwardingFilter(v: string): v is LeadForwardingStatus {
  return v === "ok" || v === "failed" || v === "not_sent";
}

/**
 * Interne Lead-Übersicht (JSON) + Inbox-Daten für `/admin/leads`.
 * Auth: `Authorization: Bearer <LEAD_ADMIN_SECRET>`, `?secret=`, oder Session-Cookie (POST /api/admin/session).
 */
export async function GET(req: Request) {
  const secret = process.env.LEAD_ADMIN_SECRET?.trim();
  if (!secret) {
    return NextResponse.json({ error: "not_configured" }, { status: 404 });
  }

  if (!isLeadAdminAuthorized(req)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const url = new URL(req.url);
  const limit = Math.min(
    2000,
    Math.max(1, parseInt(url.searchParams.get("limit") ?? "200", 10) || 200),
  );

  const rows = await readRecentLeadRecordsMerged(limit);
  const ops = await readLeadOpsState();
  let items = sortInboxItems(mergeLeadsWithOps(rows, ops));

  const triage = url.searchParams.get("triage_status")?.trim();
  const segment = url.searchParams.get("segment")?.trim();
  const sourcePage = url.searchParams.get("source_page")?.trim();
  const forwarding = url.searchParams.get("forwarding_status")?.trim();

  if (triage) {
    items = items.filter((i) => i.triage_status === triage);
  }
  if (segment) {
    items = items.filter((i) => i.segment === segment);
  }
  if (sourcePage) {
    items = items.filter((i) => i.source_page.includes(sourcePage));
  }
  if (forwarding && isForwardingFilter(forwarding)) {
    items = items.filter((i) => i.forwarding_status === forwarding);
  }

  return NextResponse.json({
    ok: true,
    count: items.length,
    items,
  });
}
