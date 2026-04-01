import { NextResponse } from "next/server";

import { isLeadAdminAuthorized } from "@/lib/leadAdminAuth";
import { mergeLeadsWithOps } from "@/lib/leadInboxMerge";
import { mutateLeadOps, readLeadOpsState } from "@/lib/leadOpsState";
import { isLeadTriageStatus, type LeadTriageStatus } from "@/lib/leadTriage";
import { findLeadInquiryRecord, getMergedLeadAdminRow } from "@/lib/leadPersistence";

export const runtime = "nodejs";

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

  const ops = await readLeadOpsState();
  const [item] = mergeLeadsWithOps([row], ops);
  return NextResponse.json({ ok: true, item });
}

type PatchBody = {
  triage_status?: string;
  owner?: string;
  internal_note?: string;
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

  if (Object.keys(patch).length === 0) {
    return NextResponse.json({ error: "empty_patch" }, { status: 400 });
  }

  const result = await mutateLeadOps(leadId, patch);
  if (!result.changed) {
    return NextResponse.json({ ok: true, changed: false, entry: result.entry });
  }

  const row = await getMergedLeadAdminRow(leadId);
  const ops = await readLeadOpsState();
  const item = row ? mergeLeadsWithOps([row], ops)[0] : null;

  return NextResponse.json({
    ok: true,
    changed: true,
    entry: result.entry,
    item,
  });
}
