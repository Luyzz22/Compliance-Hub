import type { LeadSegment } from "@/lib/leadCapture";
import type { LeadOpsActivity } from "@/lib/leadOpsTypes";
import type { LeadTriageStatus } from "@/lib/leadTriage";

export type LeadForwardingStatus = "ok" | "failed" | "not_sent";

/** Liste + Detail (intern, `/admin/leads`). */
export type LeadInboxItem = {
  lead_id: string;
  trace_id: string;
  pipeline_status: string;
  forwarding_status: LeadForwardingStatus;
  triage_status: LeadTriageStatus;
  owner: string;
  internal_note: string;
  created_at: string;
  segment: LeadSegment;
  route_key: string;
  queue_label: string;
  priority: string;
  sla_bucket: string;
  source_page: string;
  company: string;
  business_email: string;
  name: string;
  message_preview: string;
  message: string;
  webhook_ok?: boolean;
  webhook_at?: string;
  webhook_error?: string;
  needs_attention: boolean;
  activities: LeadOpsActivity[];
};
