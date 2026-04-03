import type { LeadAttributionSnapshot, LeadAttributionSource } from "@/lib/leadAttribution";
import type { LeadSegment } from "@/lib/leadCapture";
import type { LeadDuplicateHint } from "@/lib/leadIdentity";
import type { LeadDuplicateReviewStatus, LeadOpsActivity } from "@/lib/leadOpsTypes";
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
  /** Wave 30 – kanonische Attribution (aus Outbound, gespiegelt). */
  attribution_source: LeadAttributionSource;
  attribution_medium: string;
  attribution_campaign: string;
  attribution_cta_id: string;
  attribution_cta_label: string;
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
  /** Wave 27 – Kontakt-/Account-Identität (Dedup-Vorbereitung). */
  lead_contact_key: string;
  lead_account_key: string | null;
  /** Gespeichert oder nach Chronologie berechnet (attachContactRollups). */
  contact_inquiry_sequence: number;
  contact_first_seen_at: string;
  contact_latest_seen_at: string;
  duplicate_hint: LeadDuplicateHint;
  contact_submission_count: number;
  contact_has_unresolved_repeat: boolean;
  /** Weitere distinct Kontakt-Keys derselben Account-Gruppe (Firma/Domain). */
  other_contacts_on_same_account: number;
  manual_related_lead_ids: string[];
  duplicate_review: LeadDuplicateReviewStatus;
  /** Rohfelder für Detailansicht (optional leer bei alten Leads). */
  attribution: LeadAttributionSnapshot;
};

/** Timeline-Eintrag für Kontakt-Historie (Detail). */
export type LeadContactHistoryEntry = {
  lead_id: string;
  trace_id: string;
  created_at: string;
  pipeline_status: string;
  forwarding_status: LeadForwardingStatus;
  triage_status: LeadTriageStatus;
  owner: string;
  internal_note: string;
  source_page: string;
  attribution_source: LeadAttributionSource;
  attribution_medium: string;
  attribution_campaign: string;
  attribution_cta_label: string;
  segment: LeadSegment;
  message_preview: string;
  contact_inquiry_sequence: number;
  duplicate_hint: LeadDuplicateHint;
  duplicate_review: LeadDuplicateReviewStatus;
  needs_attention: boolean;
};
