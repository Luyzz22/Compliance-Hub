import { NextResponse } from "next/server";

import { isLeadAdminAuthorized } from "@/lib/leadAdminAuth";
import {
  attachContactRollups,
  buildContactHistoryItems,
  mergeLeadsWithOps,
} from "@/lib/leadInboxMerge";
import { mutateLeadOps, readLeadOpsState } from "@/lib/leadOpsState";
import type { LeadDuplicateReviewStatus } from "@/lib/leadOpsTypes";
import { isLeadTriageStatus, type LeadTriageStatus } from "@/lib/leadTriage";
import {
  findLeadInquiryRecord,
  getMergedLeadAdminRow,
  readAllLeadRecordsMerged,
} from "@/lib/leadPersistence";
import { buildProductBridgeHintForLead } from "@/lib/gtmProductBridgeAggregate";
import {
  enqueuePipedriveDealSyncIfEligible,
  processLeadSyncJobById,
  redactLeadSyncJobForApi,
} from "@/lib/leadSyncDispatcher";
import { listLeadSyncJobsForLead } from "@/lib/leadSyncStore";

export const runtime = "nodejs";

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function isDuplicateReview(v: string): v is LeadDuplicateReviewStatus {
  return v === "none" || v === "suggested" || v === "confirmed";
}

export async function GET(req: Request, ctx: { params: Promise<{ leadId: string }> }) {
  if (!process.env.LEAD_ADMIN_SECRET?.trim()) {
    return NextResponse.json({ error: "not_configured" }, { status: 404 });
  }
  if (!isLeadAdminAuthorized(req)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const { leadId } = await ctx.params;
  const row = await getMergedLeadAdminRow(leadId);
  if (!row) {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }

  const allRows = await readAllLeadRecordsMerged();
  const ops = await readLeadOpsState();
  const merged = mergeLeadsWithOps([row], ops);
  const item = attachContactRollups(merged, allRows, ops)[0] ?? merged[0]!;
  const contact_history = buildContactHistoryItems(leadId, allRows, ops);
  const sync_jobs_raw = await listLeadSyncJobsForLead(leadId);
  const sync_jobs = sync_jobs_raw.map(redactLeadSyncJobForApi);
  const product_bridge_hint = await buildProductBridgeHintForLead(item);

  return NextResponse.json({ ok: true, item, contact_history, sync_jobs, product_bridge_hint });
}

type PatchBody = {
  triage_status?: string;
  owner?: string;
  internal_note?: string;
  manual_related_lead_ids?: string[];
  duplicate_review?: string;
};

export async function PATCH(req: Request, ctx: { params: Promise<{ leadId: string }> }) {
  if (!process.env.LEAD_ADMIN_SECRET?.trim()) {
    return NextResponse.json({ error: "not_configured" }, { status: 404 });
  }
  if (!isLeadAdminAuthorized(req)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const { leadId } = await ctx.params;
  const exists = await findLeadInquiryRecord(leadId);
  if (!exists) {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }

  let body: PatchBody = {};
  try {
    body = (await req.json()) as PatchBody;
  } catch {
    return NextResponse.json({ error: "invalid_json" }, { status: 400 });
  }

  const patch: {
    triage_status?: LeadTriageStatus;
    owner?: string;
    internal_note?: string;
    manual_related_lead_ids?: string[];
    duplicate_review?: LeadDuplicateReviewStatus;
  } = {};

  if (body.triage_status !== undefined) {
    if (!isLeadTriageStatus(body.triage_status)) {
      return NextResponse.json({ error: "validation" }, { status: 400 });
    }
    patch.triage_status = body.triage_status;
  }
  if (body.owner !== undefined) {
    patch.owner = String(body.owner);
  }
  if (body.internal_note !== undefined) {
    patch.internal_note = String(body.internal_note);
  }
  if (body.duplicate_review !== undefined) {
    if (!isDuplicateReview(body.duplicate_review)) {
      return NextResponse.json({ error: "validation" }, { status: 400 });
    }
    patch.duplicate_review = body.duplicate_review;
  }
  if (body.manual_related_lead_ids !== undefined) {
    if (!Array.isArray(body.manual_related_lead_ids)) {
      return NextResponse.json({ error: "validation" }, { status: 400 });
    }
    const ids = body.manual_related_lead_ids.slice(0, 20);
    for (const id of ids) {
      if (typeof id !== "string" || !UUID_RE.test(id.trim())) {
        return NextResponse.json({ error: "validation" }, { status: 400 });
      }
      const tid = id.trim();
      if (tid === leadId) {
        return NextResponse.json({ error: "validation" }, { status: 400 });
      }
      const rec = await findLeadInquiryRecord(tid);
      if (!rec) {
        return NextResponse.json({ error: "related_not_found" }, { status: 400 });
      }
    }
    patch.manual_related_lead_ids = ids.map((x) => String(x).trim());
  }

  if (Object.keys(patch).length === 0) {
    return NextResponse.json({ error: "empty_patch" }, { status: 400 });
  }

  const result = await mutateLeadOps(leadId, patch);
  if (!result.changed) {
    return NextResponse.json({ ok: true, changed: false, entry: result.entry });
  }

  const row = await getMergedLeadAdminRow(leadId);
  const allRows = await readAllLeadRecordsMerged();
  const ops = await readLeadOpsState();
  const merged = row ? mergeLeadsWithOps([row], ops) : [];
  const item = row ? (attachContactRollups(merged, allRows, ops)[0] ?? null) : null;
  const contact_history = row ? buildContactHistoryItems(leadId, allRows, ops) : [];

  try {
    const pdJobIds = await enqueuePipedriveDealSyncIfEligible(leadId);
    for (const jid of pdJobIds) {
      await processLeadSyncJobById(jid);
    }
  } catch (e) {
    console.warn("[lead-admin] pipedrive_enqueue_process", e);
  }

  const sync_jobs_raw = await listLeadSyncJobsForLead(leadId);
  const sync_jobs = sync_jobs_raw.map(redactLeadSyncJobForApi);
  const product_bridge_hint = item ? await buildProductBridgeHintForLead(item) : null;

  return NextResponse.json({
    ok: true,
    changed: true,
    entry: result.entry,
    item,
    contact_history,
    sync_jobs,
    product_bridge_hint,
  });
}
