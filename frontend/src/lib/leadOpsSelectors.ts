import type { LeadOpsEntry, LeadOpsFile } from "@/lib/leadOpsTypes";

export function defaultLeadOpsEntry(): LeadOpsEntry {
  const now = new Date().toISOString();
  return {
    triage_status: "received",
    owner: "",
    internal_note: "",
    updated_at: now,
    activities: [],
    manual_related_lead_ids: [],
    duplicate_review: "none",
  };
}

/** Liest rohe Ops-Zeile aus Datei (ohne Defaults bei fehlenden Wave-27-Feldern). */
export function coerceOpsEntry(raw: LeadOpsEntry | undefined): LeadOpsEntry {
  if (!raw) return defaultLeadOpsEntry();
  const d = defaultLeadOpsEntry();
  return {
    ...d,
    ...raw,
    manual_related_lead_ids: raw.manual_related_lead_ids ?? d.manual_related_lead_ids,
    duplicate_review: raw.duplicate_review ?? d.duplicate_review,
    activities: raw.activities ?? d.activities,
  };
}

export function getOpsEntryForLead(state: LeadOpsFile, leadId: string): LeadOpsEntry {
  return coerceOpsEntry(state.entries[leadId]);
}
