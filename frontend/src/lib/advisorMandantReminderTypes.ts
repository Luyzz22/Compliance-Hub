/**
 * Wave 43 – Mandanten-Reminders / Follow-ups (intern, kein Task-System).
 */

/** Regelbasiert + manuell; `portfolio_attention` koppelt an die Attention-Queue. */
export type MandantReminderCategory =
  | "stale_review"
  | "stale_export"
  | "high_gap_count"
  | "portfolio_attention"
  | "sla_escalation"
  | "follow_up_note"
  | "manual";

export type MandantReminderStatus = "open" | "done" | "dismissed";

export type MandantReminderSource = "auto" | "manual";

export type MandantReminderRecord = {
  reminder_id: string;
  tenant_id: string;
  category: MandantReminderCategory;
  due_at: string;
  status: MandantReminderStatus;
  note: string | null;
  source: MandantReminderSource;
  created_at: string;
  updated_at: string;
};

export type AdvisorMandantRemindersState = {
  reminders: MandantReminderRecord[];
};

/** In Portfolio-Payload eingebettet (nur offene). */
export type MandantReminderApiEntry = {
  reminder_id: string;
  tenant_id: string;
  mandant_label: string | null;
  category: MandantReminderCategory;
  due_at: string;
  note: string | null;
  source: MandantReminderSource;
};

export const MANDANT_REMINDER_CATEGORY_LABEL_DE: Record<MandantReminderCategory, string> = {
  stale_review: "Review-Kadenz",
  stale_export: "Export-Kadenz",
  high_gap_count: "Viele offene Prüfpunkte",
  portfolio_attention: "Portfolio-Aufmerksamkeit (Queue)",
  sla_escalation: "SLA-Eskalation (Portfolio)",
  follow_up_note: "Follow-up / Notiz",
  manual: "Manuell",
};

export const MANDANT_REMINDER_MANUAL_CATEGORIES: MandantReminderCategory[] = ["manual", "follow_up_note"];
