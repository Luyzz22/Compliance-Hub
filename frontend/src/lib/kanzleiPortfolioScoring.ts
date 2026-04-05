/**
 * Kanzlei-Portfolio Attention-Score (Wave 39–40); ohne server-only für Tests.
 */

import type { BoardReadinessPillarKey, BoardReadinessTraffic } from "@/lib/boardReadinessTypes";
import {
  KANZLEI_GAP_HEAVY_FOR_EXPORT_RULE,
  KANZLEI_MANY_OPEN_POINTS,
} from "@/lib/kanzleiReviewCadenceThresholds";

export { KANZLEI_MANY_OPEN_POINTS } from "@/lib/kanzleiReviewCadenceThresholds";

const PILLAR_ORDER: BoardReadinessPillarKey[] = ["eu_ai_act", "iso_42001", "nis2", "dsgvo"];

export function kanzleiAttentionScore(input: {
  open_points_count: number;
  open_points_hoch: number;
  board_report_stale: boolean;
  any_export_stale: boolean;
  baseline_gap: boolean;
  api_fetch_ok: boolean;
  pillar_traffic: Record<BoardReadinessPillarKey, BoardReadinessTraffic>;
  review_stale: boolean;
  gaps_heavy_without_recent_export: boolean;
}): number {
  let s = 0;
  s += input.open_points_hoch * 22;
  s += Math.max(0, input.open_points_count - input.open_points_hoch) * 9;
  if (input.board_report_stale) s += 38;
  if (input.any_export_stale) s += 28;
  if (input.baseline_gap) s += 18;
  if (!input.api_fetch_ok) s += 24;
  if (input.review_stale) s += 24;
  if (input.gaps_heavy_without_recent_export) s += 26;
  for (const k of PILLAR_ORDER) {
    const st = input.pillar_traffic[k];
    if (st === "red") s += 16;
    else if (st === "amber") s += 7;
  }
  return Math.min(999, s);
}

export function computeGapsHeavyWithoutRecentExport(
  openPointsCount: number,
  anyExportStale: boolean,
): boolean {
  return openPointsCount >= KANZLEI_GAP_HEAVY_FOR_EXPORT_RULE && anyExportStale;
}
