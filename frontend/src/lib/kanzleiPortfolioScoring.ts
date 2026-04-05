/**
 * Reine Scoring-Hilfen für Kanzlei-Portfolio (Wave 39); ohne server-only für Tests.
 */

import type { BoardReadinessPillarKey, BoardReadinessTraffic } from "@/lib/boardReadinessTypes";

export const KANZLEI_EXPORT_STALE_DAYS = 45;
export const KANZLEI_MANY_OPEN_POINTS = 4;

const PILLAR_ORDER: BoardReadinessPillarKey[] = ["eu_ai_act", "iso_42001", "nis2", "dsgvo"];

export function kanzleiAttentionScore(input: {
  open_points_count: number;
  open_points_hoch: number;
  board_report_stale: boolean;
  export_stale: boolean;
  baseline_gap: boolean;
  api_fetch_ok: boolean;
  pillar_traffic: Record<BoardReadinessPillarKey, BoardReadinessTraffic>;
}): number {
  let s = 0;
  s += input.open_points_hoch * 22;
  s += Math.max(0, input.open_points_count - input.open_points_hoch) * 9;
  if (input.board_report_stale) s += 38;
  if (input.export_stale) s += 28;
  if (input.baseline_gap) s += 18;
  if (!input.api_fetch_ok) s += 24;
  for (const k of PILLAR_ORDER) {
    const st = input.pillar_traffic[k];
    if (st === "red") s += 16;
    else if (st === "amber") s += 7;
  }
  return Math.min(999, s);
}
