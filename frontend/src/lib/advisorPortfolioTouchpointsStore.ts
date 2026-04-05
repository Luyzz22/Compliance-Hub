import "server-only";

import { mkdir, readFile, writeFile } from "fs/promises";
import { dirname, join } from "path";

/**
 * Optionale manuelle Touchpoints (letzter Export / Review) pro Mandant.
 * Leere Datei oder fehlende Datei: alle Felder null im Portfolio.
 */

export type AdvisorPortfolioTouchpointEntry = {
  tenant_id: string;
  last_export_iso?: string | null;
  last_review_iso?: string | null;
  note_de?: string | null;
};

export type AdvisorPortfolioTouchpointsState = {
  entries: AdvisorPortfolioTouchpointEntry[];
};

function resolvePath(): string {
  const fromEnv = process.env.ADVISOR_PORTFOLIO_TOUCHPOINTS_PATH?.trim();
  if (fromEnv) return fromEnv;
  if (process.env.VERCEL) {
    return join("/tmp", "compliancehub-advisor-portfolio-touchpoints.json");
  }
  return join(process.cwd(), "data", "advisor-portfolio-touchpoints.json");
}

function emptyState(): AdvisorPortfolioTouchpointsState {
  return { entries: [] };
}

export async function readAdvisorPortfolioTouchpoints(): Promise<AdvisorPortfolioTouchpointsState> {
  const path = resolvePath();
  try {
    const raw = await readFile(path, "utf8");
    const o = JSON.parse(raw) as { entries?: unknown };
    if (!o || typeof o !== "object") return emptyState();
    const entries: AdvisorPortfolioTouchpointEntry[] = [];
    if (Array.isArray(o.entries)) {
      for (const e of o.entries) {
        if (!e || typeof e !== "object") continue;
        const rec = e as Record<string, unknown>;
        const tenant_id = typeof rec.tenant_id === "string" ? rec.tenant_id.trim() : "";
        if (!tenant_id) continue;
        entries.push({
          tenant_id,
          last_export_iso:
            typeof rec.last_export_iso === "string" ? rec.last_export_iso.trim() || null : null,
          last_review_iso:
            typeof rec.last_review_iso === "string" ? rec.last_review_iso.trim() || null : null,
          note_de: typeof rec.note_de === "string" ? rec.note_de.trim() || null : null,
        });
      }
    }
    return { entries };
  } catch {
    return emptyState();
  }
}

/** Für spätere Waves (z. B. Hook nach Export); aktuell kaum genutzt. */
export async function writeAdvisorPortfolioTouchpoints(
  state: AdvisorPortfolioTouchpointsState,
): Promise<void> {
  const path = resolvePath();
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, `${JSON.stringify({ entries: state.entries }, null, 2)}\n`, "utf8");
}
