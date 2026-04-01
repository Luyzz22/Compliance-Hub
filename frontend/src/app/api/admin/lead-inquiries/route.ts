import { NextResponse } from "next/server";

import { isLeadAdminAuthorized } from "@/lib/leadAdminAuth";
import {
  attachContactRollups,
  mergeLeadsWithOps,
  sortInboxItems,
} from "@/lib/leadInboxMerge";
import type { LeadForwardingStatus } from "@/lib/leadInboxTypes";
import { readLeadOpsState } from "@/lib/leadOpsState";
import { readAllLeadRecordsMerged } from "@/lib/leadPersistence";

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

  const allRows = await readAllLeadRecordsMerged();
  const pageRows = allRows.slice(0, limit);
  const ops = await readLeadOpsState();
  let items = sortInboxItems(
    attachContactRollups(mergeLeadsWithOps(pageRows, ops), allRows, ops),
  );

  const triage = url.searchParams.get("triage_status")?.trim();
  const segment = url.searchParams.get("segment")?.trim();
  const sourcePage = url.searchParams.get("source_page")?.trim();
  const forwarding = url.searchParams.get("forwarding_status")?.trim();
  const repeated = url.searchParams.get("repeated_contacts")?.trim();
  const unresolvedRep = url.searchParams.get("unresolved_repeated")?.trim();

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
  if (repeated === "1" || repeated === "true") {
    items = items.filter((i) => i.contact_submission_count > 1);
  }
  if (unresolvedRep === "1" || unresolvedRep === "true") {
    items = items.filter((i) => i.contact_has_unresolved_repeat);
  }

  return NextResponse.json({
    ok: true,
    count: items.length,
    items,
  });
}
