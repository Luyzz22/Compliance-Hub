import type { LeadOpsEntry, LeadOpsFile } from "@/lib/leadOpsTypes";

export function defaultLeadOpsEntry(): LeadOpsEntry {
  const now = new Date().toISOString();
  return {
    triage_status: "received",
    owner: "",
    internal_note: "",
    updated_at: now,
    activities: [],
  };
}

export function getOpsEntryForLead(state: LeadOpsFile, leadId: string): LeadOpsEntry {
  return state.entries[leadId] ?? defaultLeadOpsEntry();
}
