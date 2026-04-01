import type { LeadTriageStatus } from "@/lib/leadTriage";

/** Manuelle Dubletten-Einordnung (kein automatischer Merge). */
export type LeadDuplicateReviewStatus = "none" | "suggested" | "confirmed";

export type LeadOpsActivityAction =
  | "triage_status_changed"
  | "owner_set"
  | "internal_note_updated"
  | "forward_retried"
  | "ops_touch"
  | "contact_repeat_detected"
  | "manual_related_leads_updated"
  | "duplicate_review_updated"
  | "possible_duplicate_noted";

export type LeadOpsActivity = {
  at: string;
  action: LeadOpsActivityAction;
  detail?: string;
};

export type LeadOpsEntry = {
  triage_status: LeadTriageStatus;
  owner: string;
  internal_note: string;
  updated_at: string;
  activities: LeadOpsActivity[];
  /** Verknüpfung zu anderen Anfrage-IDs (manuell). */
  manual_related_lead_ids: string[];
  duplicate_review: LeadDuplicateReviewStatus;
};

export type LeadOpsFile = {
  version: number;
  entries: Record<string, LeadOpsEntry>;
};
