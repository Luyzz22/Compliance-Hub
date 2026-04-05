import "server-only";

import { mkdir, readFile, writeFile } from "fs/promises";
import { dirname, join } from "path";

import type { AdvisorKpiPortfolioSnapshot } from "@/lib/advisorKpiTypes";
import type { KanzleiPortfolioPayload } from "@/lib/kanzleiPortfolioTypes";
import {
  ADVISOR_KPI_HISTORY_FILE_VERSION,
  type AdvisorKpiHistoryPoint,
  type AdvisorKpiHistoryState,
} from "@/lib/advisorKpiHistoryTypes";

const MAX_SNAPSHOTS = 120;

function historyPath(): string {
  const fromEnv = process.env.ADVISOR_KPI_HISTORY_PATH?.trim();
  if (fromEnv) return fromEnv;
  if (process.env.VERCEL) {
    return join("/tmp", "compliancehub-advisor-kpi-history.json");
  }
  return join(process.cwd(), "data", "advisor-kpi-history.json");
}

function emptyState(): AdvisorKpiHistoryState {
  return { version: ADVISOR_KPI_HISTORY_FILE_VERSION, snapshots: [] };
}

export async function readAdvisorKpiHistoryState(): Promise<AdvisorKpiHistoryState> {
  const path = historyPath();
  try {
    const raw = await readFile(path, "utf8");
    const o = JSON.parse(raw) as Record<string, unknown>;
    if (!o || typeof o !== "object") return emptyState();
    const snaps: AdvisorKpiHistoryPoint[] = [];
    if (Array.isArray(o.snapshots)) {
      for (const e of o.snapshots) {
        if (!e || typeof e !== "object") continue;
        const r = e as Record<string, unknown>;
        if (typeof r.captured_at !== "string") continue;
        snaps.push({
          captured_at: r.captured_at,
          mapped_tenant_count: typeof r.mapped_tenant_count === "number" ? r.mapped_tenant_count : 0,
          kpi_window_days: typeof r.kpi_window_days === "number" ? r.kpi_window_days : 90,
          review_current_share: typeof r.review_current_share === "number" ? r.review_current_share : 0,
          export_fresh_share: typeof r.export_fresh_share === "number" ? r.export_fresh_share : 0,
          open_reminders_open_count:
            typeof r.open_reminders_open_count === "number" ? r.open_reminders_open_count : 0,
          share_no_open_reminders:
            typeof r.share_no_open_reminders === "number" ? r.share_no_open_reminders : 0,
          share_no_red_pillar: typeof r.share_no_red_pillar === "number" ? r.share_no_red_pillar : 0,
          reminder_median_resolution_hours:
            typeof r.reminder_median_resolution_hours === "number"
              ? r.reminder_median_resolution_hours
              : null,
        });
      }
    }
    snaps.sort((a, b) => Date.parse(a.captured_at) - Date.parse(b.captured_at));
    return { version: ADVISOR_KPI_HISTORY_FILE_VERSION, snapshots: snaps };
  } catch {
    return emptyState();
  }
}

async function writeAdvisorKpiHistoryState(state: AdvisorKpiHistoryState): Promise<void> {
  const path = historyPath();
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, `${JSON.stringify(state, null, 2)}\n`, "utf8");
}

function utcDayKey(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toISOString().slice(0, 10);
}

export function historyPointFromSnapshot(
  payload: KanzleiPortfolioPayload,
  snapshot: AdvisorKpiPortfolioSnapshot,
): AdvisorKpiHistoryPoint {
  return {
    captured_at: snapshot.generated_at,
    mapped_tenant_count: payload.mapped_tenant_count,
    kpi_window_days: snapshot.window_days,
    review_current_share: snapshot.review.current_share,
    export_fresh_share: snapshot.export_kpis.fresh_share,
    open_reminders_open_count: payload.open_reminders.length,
    share_no_open_reminders: snapshot.hygiene.share_no_open_reminders,
    share_no_red_pillar: snapshot.hygiene.share_no_red_pillar,
    reminder_median_resolution_hours: snapshot.responsiveness.reminder_median_resolution_hours,
  };
}

/**
 * Schreibt höchstens einen Eintrag pro UTC-Kalendertag (letzter Stand des Tages gewinnt).
 */
export async function upsertAdvisorKpiHistoryDaily(
  payload: KanzleiPortfolioPayload,
  snapshot: AdvisorKpiPortfolioSnapshot,
): Promise<AdvisorKpiHistoryState> {
  const state = await readAdvisorKpiHistoryState();
  const point = historyPointFromSnapshot(payload, snapshot);
  const day = utcDayKey(point.captured_at);
  if (!day) return state;

  const next = state.snapshots.filter((s) => utcDayKey(s.captured_at) !== day);
  next.push(point);
  next.sort((a, b) => Date.parse(a.captured_at) - Date.parse(b.captured_at));
  while (next.length > MAX_SNAPSHOTS) next.shift();

  const out: AdvisorKpiHistoryState = {
    version: ADVISOR_KPI_HISTORY_FILE_VERSION,
    snapshots: next,
  };
  await writeAdvisorKpiHistoryState(out);
  return out;
}
