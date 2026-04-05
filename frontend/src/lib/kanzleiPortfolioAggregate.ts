import "server-only";

import type { TenantPillarSnapshot } from "@/lib/boardReadinessAggregate";
import { loadMappedTenantPillarSnapshots } from "@/lib/boardReadinessAggregate";
import { worstTraffic } from "@/lib/boardReadinessThresholds";
import type { BoardReadinessPillarKey, BoardReadinessTraffic } from "@/lib/boardReadinessTypes";
import { readAdvisorPortfolioTouchpoints } from "@/lib/advisorPortfolioTouchpointsStore";
import type { GtmSegmentBucket } from "@/lib/gtmDashboardTypes";
import { GTM_READINESS_LABELS_DE } from "@/lib/gtmAccountReadiness";
import {
  KANZLEI_EXPORT_STALE_DAYS,
  KANZLEI_MANY_OPEN_POINTS,
  kanzleiAttentionScore,
} from "@/lib/kanzleiPortfolioScoring";
import {
  computeMandantOffenePunkte,
  pillarCodeForOpenPoint,
} from "@/lib/tenantBoardReadinessGaps";
import {
  KANZLEI_PILLAR_LABEL_DE,
  KANZLEI_PORTFOLIO_VERSION,
  type KanzleiPortfolioPayload,
  type KanzleiPortfolioRow,
} from "@/lib/kanzleiPortfolioTypes";

export { KANZLEI_EXPORT_STALE_DAYS, KANZLEI_MANY_OPEN_POINTS } from "@/lib/kanzleiPortfolioScoring";

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
  touchByTenant: Map<string, { last_export_iso?: string | null; last_review_iso?: string | null; note_de?: string | null }>,
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

  const touch = touchByTenant.get(t.tenant_id);
  const last_export_iso = touch?.last_export_iso ?? null;
  const last_review_iso = touch?.last_review_iso ?? null;
  const dExport = daysSinceIso(last_export_iso, nowMs);
  const export_stale = dExport === null || dExport > KANZLEI_EXPORT_STALE_DAYS;

  const baseline_gap = t.readiness_class === "early_pilot";

  const attention_flags_de: string[] = [];
  if (export_stale) attention_flags_de.push("Kein aktueller Export (Kanzlei) im Zeitraum");
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
    export_stale,
    baseline_gap,
    api_fetch_ok: t.raw.fetch_ok,
    pillar_traffic,
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
    last_export_iso,
    last_review_iso,
    touchpoint_note_de: touch?.note_de ?? null,
    links: {
      mandant_export_page: `/admin/advisor-mandant-export?client_id=${tidEnc}`,
      datev_bundle_api: `/api/internal/advisor/datev-export-bundle?client_id=${tidEnc}`,
      readiness_export_api: `/api/internal/advisor/mandant-readiness-export?client_id=${tidEnc}`,
      board_readiness_admin: "/admin/board-readiness",
    },
  };
}

export async function computeKanzleiPortfolioPayload(now: Date = new Date()): Promise<KanzleiPortfolioPayload> {
  const [bundle, touchState] = await Promise.all([
    loadMappedTenantPillarSnapshots(now),
    readAdvisorPortfolioTouchpoints(),
  ]);
  const nowMs = bundle.nowMs;
  const touchByTenant = new Map(
    touchState.entries.map((e) => [
      e.tenant_id,
      {
        last_export_iso: e.last_export_iso,
        last_review_iso: e.last_review_iso,
        note_de: e.note_de,
      },
    ]),
  );

  const rows = bundle.snapshots
    .map((s) => rowFromSnapshot(s, nowMs, touchByTenant))
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
      export_stale_days: KANZLEI_EXPORT_STALE_DAYS,
      many_open_points_threshold: KANZLEI_MANY_OPEN_POINTS,
    },
    rows,
  };
}
