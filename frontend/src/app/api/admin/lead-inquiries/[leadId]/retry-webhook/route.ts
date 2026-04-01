import { NextResponse } from "next/server";

import { isLeadAdminAuthorized } from "@/lib/leadAdminAuth";
import { attachContactRollups, mergeLeadsWithOps } from "@/lib/leadInboxMerge";
import { appendLeadOpsActivity, readLeadOpsState } from "@/lib/leadOpsState";
import {
  appendLeadWebhookResult,
  dispatchLeadWebhook,
  findLeadInquiryRecord,
  getMergedLeadAdminRow,
  readAllLeadRecordsMerged,
} from "@/lib/leadPersistence";

export const runtime = "nodejs";

export async function POST(req: Request, ctx: { params: Promise<{ leadId: string }> }) {
  if (!process.env.LEAD_ADMIN_SECRET?.trim()) {
    return NextResponse.json({ error: "not_configured" }, { status: 404 });
  }
  if (!isLeadAdminAuthorized(req)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const webhook = process.env.LEAD_INBOUND_WEBHOOK_URL?.trim();
  if (!webhook) {
    return NextResponse.json({ error: "webhook_not_configured" }, { status: 400 });
  }

  const { leadId } = await ctx.params;
  const record = await findLeadInquiryRecord(leadId);
  if (!record) {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }

  const wh = await dispatchLeadWebhook(webhook, record.outbound, 3);
  const at = new Date().toISOString();

  if (wh.ok) {
    await appendLeadWebhookResult({
      _kind: "webhook_result",
      lead_id: leadId,
      trace_id: record.trace_id,
      ok: true,
      at,
    });
    await appendLeadOpsActivity(leadId, "forward_retried", "Webhook: Erfolg");
  } else {
    await appendLeadWebhookResult({
      _kind: "webhook_result",
      lead_id: leadId,
      trace_id: record.trace_id,
      ok: false,
      at,
      error: wh.error,
    });
    await appendLeadOpsActivity(
      leadId,
      "forward_retried",
      `Webhook: Fehler (${wh.error})`,
    );
  }

  const row = await getMergedLeadAdminRow(leadId);
  const allRows = await readAllLeadRecordsMerged();
  const ops = await readLeadOpsState();
  const merged = row ? mergeLeadsWithOps([row], ops) : [];
  const item = row ? (attachContactRollups(merged, allRows, ops)[0] ?? null) : null;

  return NextResponse.json({
    ok: true,
    webhook_ok: wh.ok,
    webhook_error: wh.ok ? undefined : wh.error,
    item,
  });
}
