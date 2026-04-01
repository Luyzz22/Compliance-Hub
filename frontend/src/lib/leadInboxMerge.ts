import type { LeadInboxItem, LeadForwardingStatus } from "@/lib/leadInboxTypes";
import type { LeadAdminRow } from "@/lib/leadPersistence";
import type { LeadOpsFile } from "@/lib/leadOpsTypes";
import { getOpsEntryForLead } from "@/lib/leadOpsSelectors";

function forwardingStatus(r: LeadAdminRow): LeadForwardingStatus {
  if (r.webhook_ok === true) return "ok";
  if (r.webhook_ok === false) return "failed";
  return "not_sent";
}

export function mergeLeadsWithOps(rows: LeadAdminRow[], ops: LeadOpsFile): LeadInboxItem[] {
  return rows.map((r) => {
    const o = getOpsEntryForLead(ops, r.lead_id);
    const fw = forwardingStatus(r);
    const needs_attention = fw === "failed" || o.triage_status === "received";
    const ob = r.outbound;
    return {
      lead_id: r.lead_id,
      trace_id: r.trace_id,
      pipeline_status: r.status,
      forwarding_status: fw,
      triage_status: o.triage_status,
      owner: o.owner,
      internal_note: o.internal_note,
      created_at: r.created_at,
      segment: ob.segment,
      route_key: ob.route.route_key,
      queue_label: ob.route.queue_label,
      priority: ob.route.priority,
      sla_bucket: ob.route.sla_bucket,
      source_page: ob.source_page,
      company: ob.company,
      business_email: ob.business_email,
      name: ob.name,
      message_preview: ob.message.slice(0, 280),
      message: ob.message,
      webhook_ok: r.webhook_ok,
      webhook_at: r.webhook_at,
      webhook_error: r.webhook_error,
      needs_attention,
      activities: o.activities,
    };
  });
}

export function sortInboxItems(items: LeadInboxItem[]): LeadInboxItem[] {
  return [...items].sort((a, b) => {
    const na = a.needs_attention ? 0 : 1;
    const nb = b.needs_attention ? 0 : 1;
    if (na !== nb) return na - nb;
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });
}
