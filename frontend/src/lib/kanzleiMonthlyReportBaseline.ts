import "server-only";

import { mkdir, readFile, writeFile } from "fs/promises";
import { dirname, join } from "path";

import type { BoardReadinessPillarKey, BoardReadinessTraffic } from "@/lib/boardReadinessTypes";
import type { GtmReadinessClass } from "@/lib/gtmAccountReadiness";
import { rowToBaselineTenant } from "@/lib/kanzleiMonthlyReportBuild";
import type { KanzleiMonthlyBaselineTenant, KanzleiMonthlyReportBaselineState } from "@/lib/kanzleiMonthlyReportTypes";
import type { KanzleiPortfolioPayload } from "@/lib/kanzleiPortfolioTypes";

function baselinePath(): string {
  const fromEnv = process.env.KANZLEI_MONTHLY_REPORT_BASELINE_PATH?.trim();
  if (fromEnv) return fromEnv;
  if (process.env.VERCEL) {
    return join("/tmp", "compliancehub-kanzlei-monthly-report-baseline.json");
  }
  return join(process.cwd(), "data", "kanzlei-monthly-report-baseline.json");
}

function parseTraffic(x: unknown): BoardReadinessTraffic {
  if (x === "red" || x === "amber" || x === "green") return x;
  return "green";
}

function parsePillarTraffic(v: unknown): Record<BoardReadinessPillarKey, BoardReadinessTraffic> {
  const p = v && typeof v === "object" ? (v as Record<string, unknown>) : {};
  return {
    eu_ai_act: parseTraffic(p.eu_ai_act),
    iso_42001: parseTraffic(p.iso_42001),
    nis2: parseTraffic(p.nis2),
    dsgvo: parseTraffic(p.dsgvo),
  };
}

function parseReadiness(x: unknown): GtmReadinessClass | null {
  if (
    x === "no_footprint" ||
    x === "early_pilot" ||
    x === "baseline_governance" ||
    x === "advanced_governance"
  ) {
    return x;
  }
  return null;
}

function parseBand(x: unknown): KanzleiMonthlyBaselineTenant["attention_band"] {
  if (x === "low" || x === "medium" || x === "high") return x;
  return "low";
}

export async function readKanzleiMonthlyReportBaseline(): Promise<KanzleiMonthlyReportBaselineState | null> {
  const path = baselinePath();
  try {
    const raw = await readFile(path, "utf8");
    const o = JSON.parse(raw) as Record<string, unknown>;
    if (!o || typeof o.saved_at !== "string") return null;
    const tenants: KanzleiMonthlyReportBaselineState["tenants"] = {};
    const rawTenants = o.tenants;
    if (rawTenants && typeof rawTenants === "object") {
      for (const [tid, v] of Object.entries(rawTenants)) {
        if (!v || typeof v !== "object") continue;
        const rec = v as Record<string, unknown>;
        const rc = parseReadiness(rec.readiness_class);
        if (!rc) continue;
        if (typeof rec.attention_score !== "number") continue;
        tenants[tid] = {
          readiness_class: rc,
          attention_score: rec.attention_score,
          attention_band: parseBand(rec.attention_band),
          open_points_count: typeof rec.open_points_count === "number" ? rec.open_points_count : 0,
          open_points_hoch: typeof rec.open_points_hoch === "number" ? rec.open_points_hoch : 0,
          worst_traffic: parseTraffic(rec.worst_traffic),
          review_stale: Boolean(rec.review_stale),
          any_export_stale: Boolean(rec.any_export_stale),
          board_report_stale: Boolean(rec.board_report_stale),
          pillar_traffic: parsePillarTraffic(rec.pillar_traffic),
        };
      }
    }
    return {
      saved_at: o.saved_at,
      period_label: typeof o.period_label === "string" ? o.period_label : null,
      portfolio_generated_at: typeof o.portfolio_generated_at === "string" ? o.portfolio_generated_at : null,
      tenants,
    };
  } catch {
    return null;
  }
}

export async function writeKanzleiMonthlyReportBaseline(
  payload: KanzleiPortfolioPayload,
  periodLabel: string | null,
): Promise<void> {
  const path = baselinePath();
  await mkdir(dirname(path), { recursive: true });
  const tenants: KanzleiMonthlyReportBaselineState["tenants"] = {};
  for (const row of payload.rows) {
    tenants[row.tenant_id] = rowToBaselineTenant(row);
  }
  const state: KanzleiMonthlyReportBaselineState = {
    saved_at: new Date().toISOString(),
    period_label: periodLabel,
    portfolio_generated_at: payload.generated_at,
    tenants,
  };
  await writeFile(path, JSON.stringify(state, null, 2), "utf8");
}
