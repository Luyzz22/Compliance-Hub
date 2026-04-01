import { mkdir, readFile, rename, writeFile } from "fs/promises";
import { dirname, join } from "path";

import "server-only";

import type {
  LeadDuplicateReviewStatus,
  LeadOpsActivityAction,
  LeadOpsEntry,
  LeadOpsFile,
} from "@/lib/leadOpsTypes";
import { coerceOpsEntry } from "@/lib/leadOpsSelectors";
import type { LeadTriageStatus } from "@/lib/leadTriage";

const MAX_ACTIVITIES_PER_LEAD = 120;
const OPS_VERSION = 1;

export type { LeadOpsActivity, LeadOpsActivityAction, LeadOpsEntry, LeadOpsFile } from "@/lib/leadOpsTypes";

export { getOpsEntryForLead } from "@/lib/leadOpsSelectors";

function resolveOpsPath(): string {
  const fromEnv = process.env.LEAD_INQUIRY_OPS_PATH?.trim();
  if (fromEnv) return fromEnv;
  if (process.env.VERCEL) {
    return join("/tmp", "compliancehub-lead-ops-state.json");
  }
  return join(process.cwd(), "data", "lead-inquiries", "ops-state.json");
}

export async function readLeadOpsState(): Promise<LeadOpsFile> {
  const path = resolveOpsPath();
  try {
    const raw = await readFile(path, "utf8");
    const parsed = JSON.parse(raw) as LeadOpsFile;
    if (parsed?.version !== OPS_VERSION || typeof parsed.entries !== "object" || !parsed.entries) {
      return { version: OPS_VERSION, entries: {} };
    }
    return parsed;
  } catch {
    return { version: OPS_VERSION, entries: {} };
  }
}

function pushActivity(entry: LeadOpsEntry, action: LeadOpsActivityAction, detail?: string): void {
  const at = new Date().toISOString();
  entry.activities.push({ at, action, detail });
  if (entry.activities.length > MAX_ACTIVITIES_PER_LEAD) {
    entry.activities = entry.activities.slice(-MAX_ACTIVITIES_PER_LEAD);
  }
  entry.updated_at = at;
}

function sortedIds(ids: string[]): string {
  return JSON.stringify([...ids].sort());
}

export async function mutateLeadOps(
  leadId: string,
  patch: {
    triage_status?: LeadTriageStatus;
    owner?: string;
    internal_note?: string;
    manual_related_lead_ids?: string[];
    duplicate_review?: LeadDuplicateReviewStatus;
  },
): Promise<{ entry: LeadOpsEntry; path: string; changed: boolean }> {
  const path = resolveOpsPath();
  await mkdir(dirname(path), { recursive: true });

  const state = await readLeadOpsState();
  const prev = coerceOpsEntry(state.entries[leadId]);
  const nextOwner =
    patch.owner !== undefined ? patch.owner.trim().slice(0, 120) : prev.owner;
  const nextNote =
    patch.internal_note !== undefined
      ? patch.internal_note.trim().slice(0, 4000)
      : prev.internal_note;
  const nextTriage = patch.triage_status ?? prev.triage_status;
  const nextRelated =
    patch.manual_related_lead_ids !== undefined
      ? [...new Set(patch.manual_related_lead_ids.map((x) => x.trim()).filter(Boolean))].slice(0, 20)
      : prev.manual_related_lead_ids;
  const nextDupReview = patch.duplicate_review ?? prev.duplicate_review;

  const entry: LeadOpsEntry = {
    ...prev,
    triage_status: nextTriage,
    owner: nextOwner,
    internal_note: nextNote,
    manual_related_lead_ids: nextRelated,
    duplicate_review: nextDupReview,
    updated_at: prev.updated_at,
    activities: [...prev.activities],
  };

  let changed = false;
  if (patch.triage_status !== undefined && patch.triage_status !== prev.triage_status) {
    pushActivity(
      entry,
      "triage_status_changed",
      `${prev.triage_status} → ${patch.triage_status}`,
    );
    changed = true;
  }
  if (patch.owner !== undefined && nextOwner !== prev.owner) {
    pushActivity(entry, "owner_set", nextOwner || "(leer)");
    changed = true;
  }
  if (patch.internal_note !== undefined && nextNote !== prev.internal_note) {
    pushActivity(entry, "internal_note_updated", "Notiz aktualisiert");
    changed = true;
  }
  if (
    patch.manual_related_lead_ids !== undefined &&
    sortedIds(nextRelated) !== sortedIds(prev.manual_related_lead_ids)
  ) {
    pushActivity(
      entry,
      "manual_related_leads_updated",
      nextRelated.length ? nextRelated.join(", ") : "(leer)",
    );
    changed = true;
  }
  if (patch.duplicate_review !== undefined && patch.duplicate_review !== prev.duplicate_review) {
    pushActivity(
      entry,
      "duplicate_review_updated",
      `${prev.duplicate_review} → ${patch.duplicate_review}`,
    );
    changed = true;
  }

  if (!changed) {
    return { entry: prev, path, changed: false };
  }

  state.entries[leadId] = entry;

  const tmp = `${path}.tmp`;
  await writeFile(tmp, `${JSON.stringify(state, null, 0)}\n`, "utf8");
  await rename(tmp, path);
  return { entry, path, changed: true };
}

export async function appendLeadOpsActivity(
  leadId: string,
  action: LeadOpsActivityAction,
  detail?: string,
): Promise<void> {
  const path = resolveOpsPath();
  await mkdir(dirname(path), { recursive: true });
  const state = await readLeadOpsState();
  const prev = coerceOpsEntry(state.entries[leadId]);
  pushActivity(prev, action, detail);
  state.entries[leadId] = prev;
  const tmp = `${path}.tmp`;
  await writeFile(tmp, `${JSON.stringify(state, null, 0)}\n`, "utf8");
  await rename(tmp, path);
}
