import { mkdir, readFile, writeFile } from "fs/promises";
import { dirname, join } from "path";
import { randomUUID } from "crypto";

import type { GtmWeeklyReviewNote, GtmWeeklyReviewState } from "@/lib/gtmDashboardTypes";
import { utcWeekStartMondayFromMs } from "@/lib/gtmDashboardTime";

const MAX_NOTES = 40;
const NOTE_MAX_LEN = 2000;

type FileShape = {
  last_reviewed_at?: string;
  notes?: GtmWeeklyReviewNote[];
};

function resolvePath(): string {
  const fromEnv = process.env.GTM_WEEKLY_REVIEW_STORE_PATH?.trim();
  if (fromEnv) return fromEnv;
  if (process.env.VERCEL) {
    return join("/tmp", "compliancehub-gtm-weekly-review.json");
  }
  return join(process.cwd(), "data", "gtm-weekly-review.json");
}

function emptyState(): GtmWeeklyReviewState {
  return { last_reviewed_at: null, notes: [] };
}

export async function readGtmWeeklyReviewState(): Promise<GtmWeeklyReviewState> {
  const path = resolvePath();
  try {
    const raw = await readFile(path, "utf8");
    const o = JSON.parse(raw) as FileShape;
    if (!o || typeof o !== "object") return emptyState();
    const notes = Array.isArray(o.notes)
      ? o.notes.filter(
          (n): n is GtmWeeklyReviewNote =>
            typeof n === "object" &&
            n !== null &&
            typeof n.id === "string" &&
            typeof n.week_label === "string" &&
            typeof n.text === "string" &&
            typeof n.created_at === "string",
        )
      : [];
    return {
      last_reviewed_at: typeof o.last_reviewed_at === "string" ? o.last_reviewed_at : null,
      notes: notes.slice(0, MAX_NOTES),
    };
  } catch {
    return emptyState();
  }
}

export function sliceRecentNotes(state: GtmWeeklyReviewState, limit: number): GtmWeeklyReviewNote[] {
  return state.notes.slice(0, limit);
}

export async function updateGtmWeeklyReviewState(input: {
  now?: Date;
  /** Wenn true: Zeitstempel „zuletzt reviewt“ setzen. */
  mark_reviewed?: boolean;
  /** Optionale Notiz (Kalenderwoche = UTC-Montag des Zeitpunkts). */
  note?: string;
}): Promise<GtmWeeklyReviewState> {
  const now = input.now ?? new Date();
  const path = resolvePath();
  const prev = await readGtmWeeklyReviewState();
  const created_at = now.toISOString();
  const week_label = utcWeekStartMondayFromMs(now.getTime());

  let notes = [...prev.notes];
  const trimmed = input.note?.trim().slice(0, NOTE_MAX_LEN) ?? "";
  if (trimmed) {
    notes.unshift({
      id: randomUUID(),
      week_label,
      text: trimmed,
      created_at,
    });
  }
  notes = notes.slice(0, MAX_NOTES);

  const last_reviewed_at = input.mark_reviewed
    ? created_at
    : (prev.last_reviewed_at ?? null);

  const next: GtmWeeklyReviewState = {
    last_reviewed_at,
    notes,
  };

  const payload: FileShape = {
    last_reviewed_at: next.last_reviewed_at ?? undefined,
    notes: next.notes,
  };

  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
  return next;
}
