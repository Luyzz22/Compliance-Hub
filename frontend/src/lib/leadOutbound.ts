import type { LeadSegment } from "@/lib/leadCapture";
import type { LeadRoute } from "@/lib/leadRouting";

/** Stabile Webhook-/CRM-Version – bei Breaking Changes hochzählen. */
export const LEAD_OUTBOUND_SCHEMA_VERSION = "1.0" as const;

/**
 * n8n-/CRM-freundlicher Outbound-Vertrag (Wave 25).
 * Felder stabil halten; neue optionale Keys sind OK, Umbenennungen nur mit Version bump.
 */
export type LeadOutboundPayloadV1 = {
  schema_version: typeof LEAD_OUTBOUND_SCHEMA_VERSION;
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
}): LeadOutboundPayloadV1 {
  return {
    schema_version: LEAD_OUTBOUND_SCHEMA_VERSION,
    lead_id: input.lead_id,
    trace_id: input.trace_id,
    timestamp: new Date().toISOString(),
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
  };
}
