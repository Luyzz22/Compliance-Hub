import "server-only";

import type { AdvisorMandantHistoryEntry } from "@/lib/advisorMandantHistoryStore";
import { readAdvisorMandantHistoryMap } from "@/lib/advisorMandantHistoryStore";
import { maxIsoTimestamps } from "@/lib/mandantHistoryMerge";
import type { TenantPillarSnapshot } from "@/lib/boardReadinessAggregate";
import { loadMappedTenantPillarSnapshots } from "@/lib/boardReadinessAggregate";
import { worstTraffic } from "@/lib/boardReadinessThresholds";
import type { BoardReadinessPillarKey, BoardReadinessTraffic } from "@/lib/boardReadinessTypes";
import type { GtmSegmentBucket } from "@/lib/gtmDashboardTypes";
import { GTM_READINESS_LABELS_DE } from "@/lib/gtmAccountReadiness";
import {
  computeGapsHeavyWithoutRecentExport,
  kanzleiAttentionScore,
} from "@/lib/kanzleiPortfolioScoring";
import {
  KANZLEI_PILLAR_LABEL_DE,
  KANZLEI_PORTFOLIO_VERSION,
  type KanzleiPortfolioPayload,
  type KanzleiPortfolioRow,
} from "@/lib/kanzleiPortfolioTypes";
import {
  KANZLEI_ANY_EXPORT_MAX_AGE_DAYS,
  KANZLEI_GAP_HEAVY_FOR_EXPORT_RULE,
  KANZLEI_MANY_OPEN_POINTS,
  KANZLEI_REVIEW_STALE_DAYS,
} from "@/lib/kanzleiReviewCadenceThresholds";
import {
  computeMandantOffenePunkte,
  pillarCodeForOpenPoint,
} from "@/lib/tenantBoardReadinessGaps";

export {
  KANZLEI_ANY_EXPORT_MAX_AGE_DAYS,
  KANZLEI_GAP_HEAVY_FOR_EXPORT_RULE,
  KANZLEI_MANY_OPEN_POINTS,
  KANZLEI_REVIEW_STALE_DAYS,
} from "@/lib/kanzleiReviewCadenceThresholds";

const SEGMENT_LABELS_DE: Record<GtmSegmentBucket, string> = {
  industrie_mittelstand: "Industrie / Mittelstand",
  kanzlei_wp: "Kanzlei / WP",
  enterprise_sap: "Enterprise / SAP",
  other: "Sonstiges",
};

const PILLAR_ORDER: BoardReadinessPillarKey[] = ["eu_ai_act", "iso_42001", "nis2", "dsgvo"];

const PILLAR_KEY_TO_CODE: Record<BoardReadinessPillarKey, string> = {
  eu_ai_act: "EU_AI_Act",
  iso_42001: "ISO_42001",
  nis2: "NIS2",
  dsgvo: "DSGVO",
};

function trafficRank(s: BoardReadinessTraffic): number {
  if (s === "red") return 0;
  if (s === "amber") return 1;
  return 2;
}

function segmentLabel(seg: GtmSegmentBucket | null): string | null {
  if (!seg) return null;
  return SEGMENT_LABELS_DE[seg] ?? null;
}

function worstPillarFromSnapshot(t: TenantPillarSnapshot): {
  key: BoardReadinessPillarKey;
  code: string;
  label_de: string;
} {
  let best: BoardReadinessPillarKey = "eu_ai_act";
  let bestRank = 99;
  for (const key of PILLAR_ORDER) {
    const st =
      key === "eu_ai_act"
        ? t.eu.status
        : key === "iso_42001"
          ? t.iso.status
          : key === "nis2"
            ? t.nis2.status
            : t.dsgvo.status;
    const r = trafficRank(st);
    if (r < bestRank) {
      bestRank = r;
      best = key;
    }
  }
  const code = PILLAR_KEY_TO_CODE[best];
  return { key: best, code, label_de: KANZLEI_PILLAR_LABEL_DE[code] ?? code };
}

const OPEN_PILLAR_PRIORITY = ["EU_AI_Act", "ISO_42001", "NIS2", "DSGVO"] as const;

function weightedTopPillarFromOpenPoints(
  punkte: ReturnType<typeof computeMandantOffenePunkte>,
): { code: string; weight: number } | null {
  const weights: Record<string, number> = {};
  for (const p of punkte) {
    const c = pillarCodeForOpenPoint(p);
    const w = p.dringlichkeit === "hoch" ? 3 : 1;
    weights[c] = (weights[c] ?? 0) + w;
  }
  let bestCode: string | null = null;
  let bestW = 0;
  for (const c of OPEN_PILLAR_PRIORITY) {
    const w = weights[c] ?? 0;
    if (w > bestW) {
      bestW = w;
      bestCode = c;
    }
  }
  if (!bestCode || bestW <= 0) return null;
  return { code: bestCode, weight: bestW };
}

function daysSinceIso(iso: string | null | undefined, nowMs: number): number | null {
  if (!iso?.trim()) return null;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return null;
  return Math.floor((nowMs - t) / (24 * 60 * 60 * 1000));
}

function rowFromSnapshot(
  t: TenantPillarSnapshot,
  nowMs: number,
  historyByTenant: Map<string, AdvisorMandantHistoryEntry>,
): KanzleiPortfolioRow {
  const punkte = computeMandantOffenePunkte(t.tenant_id, t.raw, nowMs);
  const open_points_count = punkte.length;
  const open_points_hoch = punkte.filter((p) => p.dringlichkeit === "hoch").length;

  const weighted = weightedTopPillarFromOpenPoints(punkte);
  const worst = worstPillarFromSnapshot(t);
  const top_gap_pillar_code = weighted?.code ?? worst.code;
  const top_gap_pillar_label_de =
    KANZLEI_PILLAR_LABEL_DE[top_gap_pillar_code] ?? top_gap_pillar_code;

  const pillar_traffic: Record<BoardReadinessPillarKey, BoardReadinessTraffic> = {
    eu_ai_act: t.eu.status,
    iso_42001: t.iso.status,
    nis2: t.nis2.status,
    dsgvo: t.dsgvo.status,
  };

  const hr = t.eu.hr_total > 0;
  const board_report_stale = hr && !t.eu.board_fresh;

  const h = historyByTenant.get(t.tenant_id);
  const last_mandant_readiness_export_at = h?.last_mandant_readiness_export_at ?? null;
  const last_datev_bundle_export_at = h?.last_datev_bundle_export_at ?? null;
  const last_any_export_at = maxIsoTimestamps(last_mandant_readiness_export_at, last_datev_bundle_export_at);
  const last_review_marked_at = h?.last_review_marked_at ?? null;
  const last_review_note_de = h?.last_review_note_de ?? null;

  const never_any_export = !last_any_export_at;
  const dAny = daysSinceIso(last_any_export_at, nowMs);
  const any_export_stale = never_any_export || (dAny !== null && dAny > KANZLEI_ANY_EXPORT_MAX_AGE_DAYS);

  const dRev = daysSinceIso(last_review_marked_at, nowMs);
  const review_stale = !last_review_marked_at || (dRev !== null && dRev > KANZLEI_REVIEW_STALE_DAYS);

  const baseline_gap = t.readiness_class === "early_pilot";

  const gaps_heavy_without_recent_export = computeGapsHeavyWithoutRecentExport(
    open_points_count,
    any_export_stale,
  );

  const attention_flags_de: string[] = [];
  if (never_any_export) {
    attention_flags_de.push("Noch kein Kanzlei-Export erfasst (Readiness- oder DATEV-ZIP-Export)");
  } else if (any_export_stale) {
    attention_flags_de.push(
      `Letzter Export älter als ${KANZLEI_ANY_EXPORT_MAX_AGE_DAYS} Tage (jüngster Readiness/DATEV)`,
    );
  }
  if (review_stale) {
    attention_flags_de.push(
      `Review überfällig oder nicht erfasst (>${KANZLEI_REVIEW_STALE_DAYS} Tage)`,
    );
  }
  if (gaps_heavy_without_recent_export) {
    attention_flags_de.push(
      `Viele offene Prüfpunkte (≥${KANZLEI_GAP_HEAVY_FOR_EXPORT_RULE}) ohne frischen Export`,
    );
  }
  if (board_report_stale) attention_flags_de.push("Mandanten-/Board-Report überfällig");
  if (open_points_count >= KANZLEI_MANY_OPEN_POINTS) attention_flags_de.push("Viele offene Prüfpunkte");
  if (baseline_gap) attention_flags_de.push("Governance-Baseline noch dünn (Pilot)");
  if (!t.raw.fetch_ok) attention_flags_de.push("API teilweise nicht lesbar");

  const worstOverall = PILLAR_ORDER.reduce(
    (acc, k) => worstTraffic(acc, pillar_traffic[k]),
    "green" as BoardReadinessTraffic,
  );
  if (worstOverall === "red" && !attention_flags_de.some((x) => x.includes("überfällig"))) {
    attention_flags_de.push("Mindestens eine Säule rot");
  }

  const attention_score = kanzleiAttentionScore({
    open_points_count,
    open_points_hoch,
    board_report_stale,
    any_export_stale,
    baseline_gap,
    api_fetch_ok: t.raw.fetch_ok,
    pillar_traffic,
    review_stale,
    gaps_heavy_without_recent_export,
  });

  const tidEnc = encodeURIComponent(t.tenant_id);
  return {
    tenant_id: t.tenant_id,
    mandant_label: t.tenant_label,
    readiness_class: t.readiness_class,
    readiness_label_de: GTM_READINESS_LABELS_DE[t.readiness_class],
    primary_segment_label_de: segmentLabel(t.primary_segment),
    open_points_count,
    open_points_hoch,
    top_gap_pillar_code,
    top_gap_pillar_label_de,
    pillar_traffic,
    board_report_stale,
    api_fetch_ok: t.raw.fetch_ok,
    attention_score,
    attention_flags_de,
    last_mandant_readiness_export_at,
    last_datev_bundle_export_at,
    last_any_export_at,
    last_review_marked_at,
    last_review_note_de,
    review_stale,
    any_export_stale,
    never_any_export,
    gaps_heavy_without_recent_export,
    links: {
      mandant_export_page: `/admin/advisor-mandant-export?client_id=${tidEnc}`,
      datev_bundle_api: `/api/internal/advisor/datev-export-bundle?client_id=${tidEnc}`,
      readiness_export_api: `/api/internal/advisor/mandant-readiness-export?client_id=${tidEnc}`,
      board_readiness_admin: "/admin/board-readiness",
    },
  };
}

export async function computeKanzleiPortfolioPayload(now: Date = new Date()): Promise<KanzleiPortfolioPayload> {
  const [bundle, historyByTenant] = await Promise.all([
    loadMappedTenantPillarSnapshots(now),
    readAdvisorMandantHistoryMap(),
  ]);
  const nowMs = bundle.nowMs;

  const rows = bundle.snapshots
    .map((s) => rowFromSnapshot(s, nowMs, historyByTenant))
    .sort((a, b) => {
      if (b.attention_score !== a.attention_score) return b.attention_score - a.attention_score;
      if (b.open_points_count !== a.open_points_count) return b.open_points_count - a.open_points_count;
      return (a.mandant_label ?? a.tenant_id).localeCompare(b.mandant_label ?? b.tenant_id, "de");
    });

  return {
    version: KANZLEI_PORTFOLIO_VERSION,
    generated_at: bundle.generated_at,
    backend_reachable: bundle.backend_reachable,
    mapped_tenant_count: bundle.tenantIds.length,
    tenants_partial: bundle.tenants_partial,
    constants: {
      review_stale_days: KANZLEI_REVIEW_STALE_DAYS,
      any_export_max_age_days: KANZLEI_ANY_EXPORT_MAX_AGE_DAYS,
      many_open_points_threshold: KANZLEI_MANY_OPEN_POINTS,
      gap_heavy_min_open_for_export_rule: KANZLEI_GAP_HEAVY_FOR_EXPORT_RULE,
    },
    rows,
  };
}
