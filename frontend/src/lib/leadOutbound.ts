import type { LeadSegment } from "@/lib/leadCapture";
import type { LeadDuplicateHint } from "@/lib/leadIdentity";
import type { LeadRoute } from "@/lib/leadRouting";

/** Stabile Webhook-/CRM-Version – bei Breaking Changes hochzählen. */
export const LEAD_OUTBOUND_SCHEMA_VERSION = "1.1" as const;

export type LeadOutboundSchemaVersion = "1.0" | "1.1";

/**
 * n8n-/CRM-freundlicher Outbound-Vertrag (Wave 25, erweitert Wave 27).
 * Neue Anfragen nutzen `1.1` inkl. Identity-Feldern; ältere JSONL-Zeilen können `1.0` sein.
 */
export type LeadOutboundPayloadV1 = {
  schema_version: LeadOutboundSchemaVersion;
  lead_id: string;
  trace_id: string;
  timestamp: string;
  source_page: string;
  segment: LeadSegment;
  name: string;
  business_email: string;
  company: string;
  message: string;
  route: {
    route_key: string;
    queue_label: string;
    priority: LeadRoute["priority"];
    sla_bucket: LeadRoute["sla_bucket"];
  };
  /** Wave 27 – nur bei schema_version 1.1 gesetzt (CRM/n8n Dedup-Vorbereitung). */
  lead_contact_key?: string;
  lead_account_key?: string | null;
  contact_inquiry_sequence?: number;
  contact_first_seen_at?: string;
  contact_latest_seen_at?: string;
  duplicate_hint?: LeadDuplicateHint;
};

export type LeadOutboundIdentitySnapshot = {
  lead_contact_key: string;
  lead_account_key: string | null;
  contact_inquiry_sequence: number;
  contact_first_seen_at: string;
  contact_latest_seen_at: string;
  duplicate_hint: LeadDuplicateHint;
};

export function buildLeadOutboundPayload(input: {
  lead_id: string;
  trace_id: string;
  source_page: string;
  segment: LeadSegment;
  name: string;
  work_email: string;
  company: string;
  message: string;
  route: LeadRoute;
  identity: LeadOutboundIdentitySnapshot;
  /** Optional: gleicher Zeitstempel wie JSONL-Zeile (Persistenz/Webhook konsistent). */
  timestamp?: string;
}): LeadOutboundPayloadV1 {
  const { identity } = input;
  return {
    schema_version: LEAD_OUTBOUND_SCHEMA_VERSION,
    lead_id: input.lead_id,
    trace_id: input.trace_id,
    timestamp: input.timestamp ?? new Date().toISOString(),
    source_page: input.source_page,
    segment: input.segment,
    name: input.name,
    business_email: input.work_email,
    company: input.company,
    message: input.message,
    route: {
      route_key: input.route.route_key,
      queue_label: input.route.queue_label,
      priority: input.route.priority,
      sla_bucket: input.route.sla_bucket,
    },
    lead_contact_key: identity.lead_contact_key,
    lead_account_key: identity.lead_account_key,
    contact_inquiry_sequence: identity.contact_inquiry_sequence,
    contact_first_seen_at: identity.contact_first_seen_at,
    contact_latest_seen_at: identity.contact_latest_seen_at,
    duplicate_hint: identity.duplicate_hint,
  };
}
