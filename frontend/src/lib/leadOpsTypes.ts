import type { LeadTriageStatus } from "@/lib/leadTriage";

export type LeadOpsActivityAction =
  | "triage_status_changed"
  | "owner_set"
  | "internal_note_updated"
  | "forward_retried"
  | "ops_touch";

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
};

export type LeadOpsFile = {
  version: number;
  entries: Record<string, LeadOpsEntry>;
};
