import type { BoardReadinessTraffic } from "@/lib/boardReadinessTypes";

/** Schwellen bewusst grob (Wave 34); siehe docs/board/wave34-board-readiness-dashboard.md */
export const BOARD_REPORT_FRESH_DAYS = 90;

export function trafficFromRatio(ratio: number | null): BoardReadinessTraffic {
  if (ratio === null || Number.isNaN(ratio)) return "amber";
  if (ratio >= 0.75) return "green";
  if (ratio < 0.45) return "red";
  return "amber";
}

export function worstTraffic(a: BoardReadinessTraffic, b: BoardReadinessTraffic): BoardReadinessTraffic {
  const rank: Record<BoardReadinessTraffic, number> = { green: 0, amber: 1, red: 2 };
  return rank[a] >= rank[b] ? a : b;
}
