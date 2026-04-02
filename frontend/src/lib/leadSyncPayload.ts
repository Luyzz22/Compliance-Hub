import { createHash } from "crypto";

import type { LeadInboxItem } from "@/lib/leadInboxTypes";
import type { LeadAdminRow } from "@/lib/leadPersistence";
import type { LeadSyncPayloadV1, LeadSyncTarget } from "@/lib/leadSyncTypes";

export const LEAD_SYNC_PAYLOAD_VERSION = "1.0" as const;

export type LegacyInboundDelivery =
  | "forwarded"
  | "stored"
  | "stored_forward_failed"
  | "not_configured";

function forwardingToStatus(row: LeadAdminRow): "ok" | "failed" | "not_sent" {
  if (row.webhook_ok === true) return "ok";
  if (row.webhook_ok === false) return "failed";
  return "not_sent";
}

/**
 * Deterministisch: gleicher Target + Lead + Payload-Version + Material-Revision → gleicher Key.
 * Revision = created_at der Inquiry (immutable); später z. B. `triage:${updated_at}` für Re-Sync.
 */
export function computeLeadSyncIdempotencyKey(
  target: LeadSyncTarget,
  leadId: string,
  payloadVersion: string,
  materialRevision: string,
): string {
  const raw = `sync_idemp_v1|${target}|${leadId}|${payloadVersion}|${materialRevision}`;
  return `idem_${createHash("sha256").update(raw, "utf8").digest("hex").slice(0, 40)}`;
}

export function defaultMaterialRevisionForIngest(createdAtIso: string): string {
  return `ingest:${createdAtIso}`;
}

export function buildLeadSyncPayloadV1(input: {
  row: LeadAdminRow;
  inboxItem: LeadInboxItem;
  legacyInboundDelivery: LegacyInboundDelivery;
  idempotency_key: string;
}): LeadSyncPayloadV1 {
  const { row, inboxItem, legacyInboundDelivery, idempotency_key } = input;
  const ob = row.outbound;
  const fw = forwardingToStatus(row);
  const forwarding_status = fw === "ok" ? "ok" : fw === "failed" ? "failed" : "not_sent";
  return {
    schema_version: "1.0",
    idempotency_key,
    lead_id: row.lead_id,
    trace_id: row.trace_id,
    created_at: row.created_at,
    source_page: ob.source_page,
    segment: ob.segment,
    name: ob.name,
    business_email: ob.business_email,
    company: ob.company,
    message: ob.message,
    route: {
      route_key: ob.route.route_key,
      queue_label: ob.route.queue_label,
      priority: ob.route.priority,
      sla_bucket: ob.route.sla_bucket,
    },
    lead_contact_key: inboxItem.lead_contact_key,
    lead_account_key: inboxItem.lead_account_key,
    contact_inquiry_sequence: inboxItem.contact_inquiry_sequence,
    contact_first_seen_at: inboxItem.contact_first_seen_at,
    contact_latest_seen_at: inboxItem.contact_latest_seen_at,
    contact_submission_count: inboxItem.contact_submission_count,
    duplicate_hint: inboxItem.duplicate_hint,
    triage_status: inboxItem.triage_status,
    owner: inboxItem.owner,
    pipeline_status: row.status,
    forwarding_status,
    legacy_inbound_webhook_delivery: legacyInboundDelivery,
  };
}
