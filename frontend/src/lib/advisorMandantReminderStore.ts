import "server-only";

import { randomUUID } from "crypto";
import { mkdir, readFile, writeFile } from "fs/promises";
import { dirname, join } from "path";

import type { KanzleiAttentionQueueItem, KanzleiPortfolioRow } from "@/lib/kanzleiPortfolioTypes";
import {
  AUTO_MANDANT_REMINDER_CATEGORIES,
  defaultAutoDueAtIso,
  isAutoReminderConditionActive,
} from "@/lib/advisorMandantReminderRules";
import type {
  AdvisorMandantRemindersState,
  MandantReminderCategory,
  MandantReminderRecord,
  MandantReminderStatus,
} from "@/lib/advisorMandantReminderTypes";
import { MANDANT_REMINDER_MANUAL_CATEGORIES } from "@/lib/advisorMandantReminderTypes";

function remindersPath(): string {
  const fromEnv = process.env.ADVISOR_MANDANT_REMINDERS_PATH?.trim();
  if (fromEnv) return fromEnv;
  if (process.env.VERCEL) {
    return join("/tmp", "compliancehub-advisor-mandant-reminders.json");
  }
  return join(process.cwd(), "data", "advisor-mandant-reminders.json");
}

function emptyState(): AdvisorMandantRemindersState {
  return { reminders: [] };
}

export async function readAdvisorMandantRemindersState(): Promise<AdvisorMandantRemindersState> {
  const path = remindersPath();
  try {
    const raw = await readFile(path, "utf8");
    const o = JSON.parse(raw) as { reminders?: unknown };
    if (!o || !Array.isArray(o.reminders)) return emptyState();
    const reminders: MandantReminderRecord[] = [];
    for (const e of o.reminders) {
      if (!e || typeof e !== "object") continue;
      const r = e as Record<string, unknown>;
      if (typeof r.reminder_id !== "string" || typeof r.tenant_id !== "string") continue;
      if (typeof r.category !== "string") continue;
      if (typeof r.due_at !== "string") continue;
      if (r.status !== "open" && r.status !== "done" && r.status !== "dismissed") continue;
      if (r.source !== "auto" && r.source !== "manual") continue;
      reminders.push({
        reminder_id: r.reminder_id,
        tenant_id: r.tenant_id.trim(),
        category: r.category as MandantReminderCategory,
        due_at: r.due_at,
        status: r.status,
        note: typeof r.note === "string" ? r.note : null,
        source: r.source,
        created_at: typeof r.created_at === "string" ? r.created_at : new Date().toISOString(),
        updated_at: typeof r.updated_at === "string" ? r.updated_at : new Date().toISOString(),
      });
    }
    return { reminders };
  } catch {
    return emptyState();
  }
}

async function writeAdvisorMandantRemindersState(state: AdvisorMandantRemindersState): Promise<void> {
  const path = remindersPath();
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, JSON.stringify(state, null, 2), "utf8");
}

function findOpenAuto(state: AdvisorMandantRemindersState, tenantId: string, category: MandantReminderCategory) {
  return state.reminders.find(
    (x) => x.tenant_id === tenantId && x.category === category && x.status === "open" && x.source === "auto",
  );
}

/**
 * Synchronisiert Auto-Reminder mit Portfolio-Zeilen: anlegen, erledigen wenn Bedingung wegfällt.
 */
export async function syncAdvisorMandantRemindersFromPortfolio(
  rows: KanzleiPortfolioRow[],
  manyOpenThreshold: number,
  nowMs: number,
): Promise<AdvisorMandantRemindersState> {
  const state = await readAdvisorMandantRemindersState();
  const isoNow = new Date(nowMs).toISOString();

  for (const row of rows) {
    for (const category of AUTO_MANDANT_REMINDER_CATEGORIES) {
      const active = isAutoReminderConditionActive(row, category, manyOpenThreshold);
      const open = findOpenAuto(state, row.tenant_id, category);

      if (!active && open) {
        open.status = "done";
        open.updated_at = isoNow;
      }

      if (active && !open) {
        state.reminders.push({
          reminder_id: randomUUID(),
          tenant_id: row.tenant_id,
          category,
          due_at: defaultAutoDueAtIso(nowMs),
          status: "open",
          note: null,
          source: "auto",
          created_at: isoNow,
          updated_at: isoNow,
        });
      }
    }
  }

  await writeAdvisorMandantRemindersState(state);
  return state;
}

const SLA_ESCALATION_NOTE_DE =
  "Wave 47 SLA: Portfolio eskaliert – mit Partner abstimmen und Queue priorisieren (automatisch).";

/**
 * Legt bei aktiven Eskalationssignalen Auto-Reminder (max. Top-3 Queue) an, sonst schließt SLA-Auto-Reminder.
 */
export async function syncAdvisorSlaEscalationReminders(
  attentionQueue: KanzleiAttentionQueueItem[],
  escalate: boolean,
  nowMs: number,
): Promise<void> {
  const state = await readAdvisorMandantRemindersState();
  const isoNow = new Date(nowMs).toISOString();

  const closeOpenSlaAuto = () => {
    for (const r of state.reminders) {
      if (r.category === "sla_escalation" && r.source === "auto" && r.status === "open") {
        r.status = "done";
        r.updated_at = isoNow;
      }
    }
  };

  if (!escalate) {
    closeOpenSlaAuto();
    await writeAdvisorMandantRemindersState(state);
    return;
  }

  const top = attentionQueue.slice(0, 3);
  const activeTenants = new Set(top.map((t) => t.tenant_id));

  for (const r of state.reminders) {
    if (r.category !== "sla_escalation" || r.source !== "auto" || r.status !== "open") continue;
    if (!activeTenants.has(r.tenant_id)) {
      r.status = "done";
      r.updated_at = isoNow;
    }
  }

  for (const q of top) {
    const open = state.reminders.find(
      (x) =>
        x.tenant_id === q.tenant_id &&
        x.category === "sla_escalation" &&
        x.source === "auto" &&
        x.status === "open",
    );
    if (!open) {
      state.reminders.push({
        reminder_id: randomUUID(),
        tenant_id: q.tenant_id,
        category: "sla_escalation",
        due_at: defaultAutoDueAtIso(nowMs),
        status: "open",
        note: SLA_ESCALATION_NOTE_DE,
        source: "auto",
        created_at: isoNow,
        updated_at: isoNow,
      });
    }
  }

  await writeAdvisorMandantRemindersState(state);
}

export async function createAdvisorMandantReminderManual(input: {
  tenant_id: string;
  category: MandantReminderCategory;
  note: string | null;
  due_at: string;
}): Promise<MandantReminderRecord> {
  if (!MANDANT_REMINDER_MANUAL_CATEGORIES.includes(input.category)) {
    throw new Error("invalid_manual_category");
  }
  const state = await readAdvisorMandantRemindersState();
  const isoNow = new Date().toISOString();
  const rec: MandantReminderRecord = {
    reminder_id: randomUUID(),
    tenant_id: input.tenant_id.trim(),
    category: input.category,
    due_at: input.due_at.trim(),
    status: "open",
    note: input.note?.trim() ? input.note.trim().slice(0, 500) : null,
    source: "manual",
    created_at: isoNow,
    updated_at: isoNow,
  };
  state.reminders.push(rec);
  await writeAdvisorMandantRemindersState(state);
  return rec;
}

export async function updateAdvisorMandantReminderStatus(
  reminderId: string,
  status: MandantReminderStatus,
): Promise<MandantReminderRecord | null> {
  if (status !== "done" && status !== "dismissed") return null;
  const state = await readAdvisorMandantRemindersState();
  const rec = state.reminders.find((x) => x.reminder_id === reminderId);
  if (!rec || rec.status !== "open") return null;
  rec.status = status;
  rec.updated_at = new Date().toISOString();
  await writeAdvisorMandantRemindersState(state);
  return rec;
}

export async function listAdvisorMandantReminders(filters?: {
  tenant_id?: string;
  status?: MandantReminderStatus;
}): Promise<MandantReminderRecord[]> {
  const state = await readAdvisorMandantRemindersState();
  let out = state.reminders;
  if (filters?.tenant_id?.trim()) {
    const t = filters.tenant_id.trim();
    out = out.filter((x) => x.tenant_id === t);
  }
  if (filters?.status) {
    out = out.filter((x) => x.status === filters.status);
  }
  return out.sort((a, b) => Date.parse(a.due_at) - Date.parse(b.due_at));
}
