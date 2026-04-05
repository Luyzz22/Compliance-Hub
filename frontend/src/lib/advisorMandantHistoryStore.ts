import "server-only";

import { mkdir, readFile, writeFile } from "fs/promises";
import { dirname, join } from "path";

import type { AdvisorMandantHistoryApiDto } from "@/lib/kanzleiPortfolioTypes";
import {
  KANZLEI_ANY_EXPORT_MAX_AGE_DAYS,
  KANZLEI_REVIEW_STALE_DAYS,
} from "@/lib/kanzleiReviewCadenceThresholds";
import { maxIsoTimestamps } from "@/lib/mandantHistoryMerge";

/**
 * Persistente Kanzlei-Historie pro Mandant (Wave 40): Export-Zeitpunkte und Review-Markierung.
 * Datei: data/advisor-mandant-history.json (oder ADVISOR_MANDANT_HISTORY_PATH).
 * Liest optional legacy advisor-portfolio-touchpoints.json ein (Migration Wave 39).
 */

export type AdvisorMandantHistoryEntry = {
  tenant_id: string;
  last_mandant_readiness_export_at: string | null;
  last_datev_bundle_export_at: string | null;
  last_review_marked_at: string | null;
  last_review_note_de: string | null;
};

export type AdvisorMandantHistoryState = {
  entries: AdvisorMandantHistoryEntry[];
};

function historyPath(): string {
  const fromEnv = process.env.ADVISOR_MANDANT_HISTORY_PATH?.trim();
  if (fromEnv) return fromEnv;
  if (process.env.VERCEL) {
    return join("/tmp", "compliancehub-advisor-mandant-history.json");
  }
  return join(process.cwd(), "data", "advisor-mandant-history.json");
}

function legacyTouchpointsPath(): string {
  const fromEnv = process.env.ADVISOR_PORTFOLIO_TOUCHPOINTS_PATH?.trim();
  if (fromEnv) return fromEnv;
  if (process.env.VERCEL) {
    return join("/tmp", "compliancehub-advisor-portfolio-touchpoints.json");
  }
  return join(process.cwd(), "data", "advisor-portfolio-touchpoints.json");
}

function emptyEntry(tenantId: string): AdvisorMandantHistoryEntry {
  return {
    tenant_id: tenantId,
    last_mandant_readiness_export_at: null,
    last_datev_bundle_export_at: null,
    last_review_marked_at: null,
    last_review_note_de: null,
  };
}

function emptyState(): AdvisorMandantHistoryState {
  return { entries: [] };
}

async function readRawHistoryFile(): Promise<AdvisorMandantHistoryState> {
  const path = historyPath();
  try {
    const raw = await readFile(path, "utf8");
    const o = JSON.parse(raw) as { entries?: unknown };
    if (!o || typeof o !== "object") return emptyState();
    const entries: AdvisorMandantHistoryEntry[] = [];
    if (Array.isArray(o.entries)) {
      for (const e of o.entries) {
        if (!e || typeof e !== "object") continue;
        const rec = e as Record<string, unknown>;
        const tenant_id = typeof rec.tenant_id === "string" ? rec.tenant_id.trim() : "";
        if (!tenant_id) continue;
        entries.push({
          tenant_id,
          last_mandant_readiness_export_at:
            typeof rec.last_mandant_readiness_export_at === "string"
              ? rec.last_mandant_readiness_export_at.trim() || null
              : null,
          last_datev_bundle_export_at:
            typeof rec.last_datev_bundle_export_at === "string"
              ? rec.last_datev_bundle_export_at.trim() || null
              : null,
          last_review_marked_at:
            typeof rec.last_review_marked_at === "string"
              ? rec.last_review_marked_at.trim() || null
              : null,
          last_review_note_de:
            typeof rec.last_review_note_de === "string" ? rec.last_review_note_de.trim() || null : null,
        });
      }
    }
    return { entries };
  } catch {
    return emptyState();
  }
}

type LegacyTouchRow = {
  tenant_id: string;
  last_export_iso?: string | null;
  last_review_iso?: string | null;
  note_de?: string | null;
};

async function readLegacyTouchpointsRows(): Promise<LegacyTouchRow[]> {
  const path = legacyTouchpointsPath();
  try {
    const raw = await readFile(path, "utf8");
    const o = JSON.parse(raw) as { entries?: unknown };
    if (!o || !Array.isArray(o.entries)) return [];
    const out: LegacyTouchRow[] = [];
    for (const e of o.entries) {
      if (!e || typeof e !== "object") continue;
      const rec = e as Record<string, unknown>;
      const tenant_id = typeof rec.tenant_id === "string" ? rec.tenant_id.trim() : "";
      if (!tenant_id) continue;
      out.push({
        tenant_id,
        last_export_iso:
          typeof rec.last_export_iso === "string" ? rec.last_export_iso.trim() || null : null,
        last_review_iso:
          typeof rec.last_review_iso === "string" ? rec.last_review_iso.trim() || null : null,
        note_de: typeof rec.note_de === "string" ? rec.note_de.trim() || null : null,
      });
    }
    return out;
  } catch {
    return [];
  }
}

function mergeLegacyIntoMap(map: Map<string, AdvisorMandantHistoryEntry>, legacy: LegacyTouchRow[]): void {
  for (const row of legacy) {
    const cur = map.get(row.tenant_id) ?? emptyEntry(row.tenant_id);
    const merged: AdvisorMandantHistoryEntry = {
      tenant_id: row.tenant_id,
      last_mandant_readiness_export_at: maxIsoTimestamps(
        cur.last_mandant_readiness_export_at,
        row.last_export_iso,
      ),
      last_datev_bundle_export_at: cur.last_datev_bundle_export_at,
      last_review_marked_at: maxIsoTimestamps(cur.last_review_marked_at, row.last_review_iso),
      last_review_note_de: cur.last_review_note_de ?? row.note_de ?? null,
    };
    map.set(row.tenant_id, merged);
  }
}

/**
 * Alle Einträge als Map (inkl. Legacy-Touchpoints aus Wave 39, falls vorhanden).
 */
export async function readAdvisorMandantHistoryMap(): Promise<Map<string, AdvisorMandantHistoryEntry>> {
  const base = await readRawHistoryFile();
  const map = new Map<string, AdvisorMandantHistoryEntry>();
  for (const e of base.entries) {
    map.set(e.tenant_id, { ...e });
  }
  const legacy = await readLegacyTouchpointsRows();
  mergeLegacyIntoMap(map, legacy);
  return map;
}

export async function readAdvisorMandantHistoryEntry(
  tenantId: string,
): Promise<AdvisorMandantHistoryEntry> {
  const m = await readAdvisorMandantHistoryMap();
  return m.get(tenantId) ?? emptyEntry(tenantId);
}

async function writeHistoryState(state: AdvisorMandantHistoryState): Promise<void> {
  const path = historyPath();
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, `${JSON.stringify({ entries: state.entries }, null, 2)}\n`, "utf8");
}

export async function recordMandantReadinessExport(tenantId: string, atIso?: string): Promise<void> {
  const t = (atIso ?? new Date().toISOString()).trim();
  const tid = tenantId.trim();
  if (!tid) return;
  const state = await readRawHistoryFile();
  const idx = state.entries.findIndex((e) => e.tenant_id === tid);
  const prev = idx >= 0 ? state.entries[idx]! : emptyEntry(tid);
  const next: AdvisorMandantHistoryEntry = {
    ...prev,
    tenant_id: tid,
    last_mandant_readiness_export_at: maxIsoTimestamps(prev.last_mandant_readiness_export_at, t),
  };
  const entries = [...state.entries.filter((e) => e.tenant_id !== tid), next];
  entries.sort((a, b) => a.tenant_id.localeCompare(b.tenant_id));
  await writeHistoryState({ entries });
}

export async function recordDatevBundleExport(tenantId: string, atIso?: string): Promise<void> {
  const t = (atIso ?? new Date().toISOString()).trim();
  const tid = tenantId.trim();
  if (!tid) return;
  const state = await readRawHistoryFile();
  const idx = state.entries.findIndex((e) => e.tenant_id === tid);
  const prev = idx >= 0 ? state.entries[idx]! : emptyEntry(tid);
  const next: AdvisorMandantHistoryEntry = {
    ...prev,
    tenant_id: tid,
    last_datev_bundle_export_at: maxIsoTimestamps(prev.last_datev_bundle_export_at, t),
  };
  const entries = [...state.entries.filter((e) => e.tenant_id !== tid), next];
  entries.sort((a, b) => a.tenant_id.localeCompare(b.tenant_id));
  await writeHistoryState({ entries });
}

export async function recordAdvisorReviewMarked(
  tenantId: string,
  noteDe: string | undefined,
  atIso?: string,
): Promise<void> {
  const t = (atIso ?? new Date().toISOString()).trim();
  const tid = tenantId.trim();
  if (!tid) return;
  const state = await readRawHistoryFile();
  const idx = state.entries.findIndex((e) => e.tenant_id === tid);
  const prev = idx >= 0 ? state.entries[idx]! : emptyEntry(tid);
  const nextNote =
    noteDe === undefined
      ? prev.last_review_note_de
      : noteDe.trim()
        ? noteDe.trim().slice(0, 500)
        : null;
  const next: AdvisorMandantHistoryEntry = {
    ...prev,
    tenant_id: tid,
    last_review_marked_at: t,
    last_review_note_de: nextNote,
  };
  const entries = [...state.entries.filter((e) => e.tenant_id !== tid), next];
  entries.sort((a, b) => a.tenant_id.localeCompare(b.tenant_id));
  await writeHistoryState({ entries });
}

function daysSinceIsoLocal(iso: string | null | undefined, nowMs: number): number | null {
  if (!iso?.trim()) return null;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return null;
  return Math.floor((nowMs - t) / (24 * 60 * 60 * 1000));
}

export async function getAdvisorMandantHistoryApiDto(
  tenantId: string,
  nowMs: number = Date.now(),
): Promise<AdvisorMandantHistoryApiDto> {
  const entry = await readAdvisorMandantHistoryEntry(tenantId.trim());
  const last_any_export_at = maxIsoTimestamps(
    entry.last_mandant_readiness_export_at,
    entry.last_datev_bundle_export_at,
  );
  const never_any_export = !last_any_export_at;
  const dAny = daysSinceIsoLocal(last_any_export_at, nowMs);
  const any_export_stale = never_any_export || (dAny !== null && dAny > KANZLEI_ANY_EXPORT_MAX_AGE_DAYS);
  const dRev = daysSinceIsoLocal(entry.last_review_marked_at, nowMs);
  const review_stale =
    !entry.last_review_marked_at || (dRev !== null && dRev > KANZLEI_REVIEW_STALE_DAYS);

  return {
    tenant_id: entry.tenant_id,
    last_mandant_readiness_export_at: entry.last_mandant_readiness_export_at,
    last_datev_bundle_export_at: entry.last_datev_bundle_export_at,
    last_any_export_at,
    last_review_marked_at: entry.last_review_marked_at,
    last_review_note_de: entry.last_review_note_de,
    review_stale,
    any_export_stale,
    never_any_export,
    constants: {
      review_stale_days: KANZLEI_REVIEW_STALE_DAYS,
      any_export_max_age_days: KANZLEI_ANY_EXPORT_MAX_AGE_DAYS,
    },
  };
}
