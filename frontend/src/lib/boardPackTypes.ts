/**
 * Wave 36 – Quarterly Board Pack (lightweight export from Board Readiness).
 */

import type { BoardReadinessPillarKey, BoardReadinessTraffic } from "@/lib/boardReadinessTypes";

export const BOARD_PACK_VERSION = "wave36-v1";

/** Säule oder Portfolio-/GTM-Querschnitt */
export type BoardPackPillarKey = BoardReadinessPillarKey | "portfolio";

export type BoardPackHorizon = "now" | "this_quarter" | "next_quarter";

export type BoardPackHorizonLabelDe = Record<BoardPackHorizon, string>;

export const BOARD_PACK_HORIZON_LABEL_DE: BoardPackHorizonLabelDe = {
  now: "Jetzt (≤ 14 Tage)",
  this_quarter: "Dieses Quartal",
  next_quarter: "Nächstes Quartal",
};

/** Teil A – Executive Memo */
export type BoardPackExecutiveMemo = {
  title_de: string;
  /** Eine Zeile pro Säule: Ampel + Kurzkommentar */
  pillar_headlines_de: string[];
  /** Explizite Delta-Zeilen (Baseline) */
  changes_since_baseline_de: string[];
  /** Risiken / Fokusthemen (faktisch, keine Rechtsfolge) */
  key_risks_and_concerns_de: string[];
};

/** Teil B – priorisiertes Attention-Item für den Pack */
export type BoardPackAttentionRow = {
  priority_rank: number;
  priority_rule_de: string;
  severity: BoardReadinessTraffic;
  summary_de: string;
  reference_id: string;
  tenant_label_de: string;
  pillar_hint: BoardPackPillarKey;
};

/** Teil C – Aktionsregister */
export type BoardPackActionRow = {
  id: string;
  priority_rank: number;
  action_de: string;
  pillar: BoardPackPillarKey;
  /** Bekannt aus Daten oder Platzhalter */
  owner_de: string;
  horizon: BoardPackHorizon;
  reference_ids: string[];
  source_attention_id?: string;
};

export type BoardPackMetadata = {
  generated_at: string;
  source_board_readiness_generated_at: string;
  baseline_saved_at: string | null;
  baseline_board_readiness_generated_at: string | null;
  scope_de: string;
  mapped_tenant_count: number;
  backend_reachable: boolean;
  attention_rows_count: number;
  action_rows_count: number;
  prioritization_rules_de: string[];
};

export type BoardPackPayload = {
  version: typeof BOARD_PACK_VERSION;
  memo: BoardPackExecutiveMemo;
  attention: BoardPackAttentionRow[];
  actions: BoardPackActionRow[];
  markdown_de: string;
  meta: BoardPackMetadata;
};
