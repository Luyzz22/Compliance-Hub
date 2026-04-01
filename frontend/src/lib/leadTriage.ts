/**
 * Interne Lead-Triage (Wave 26) – kein CRM, nur operative Einordnung.
 */

export const LEAD_TRIAGE_STATUSES = [
  "received",
  "triaged",
  "contacted",
  "qualified",
  "closed_won_interest",
  "closed_not_now",
  "spam",
] as const;

export type LeadTriageStatus = (typeof LEAD_TRIAGE_STATUSES)[number];

const TRIAGE_SET = new Set<string>(LEAD_TRIAGE_STATUSES);

export function isLeadTriageStatus(v: string): v is LeadTriageStatus {
  return TRIAGE_SET.has(v);
}

/** Kurzlabels für UI (DACH-B2B, intern) */
export const LEAD_TRIAGE_LABELS_DE: Record<LeadTriageStatus, string> = {
  received: "Neu / unbearbeitet",
  triaged: "Triage erledigt",
  contacted: "Kontaktiert",
  qualified: "Qualifiziert",
  closed_won_interest: "Abschluss-Interesse",
  closed_not_now: "Zurückgestellt",
  spam: "Spam / ungültig",
};
