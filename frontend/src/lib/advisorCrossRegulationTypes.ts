/**
 * Wave 49 – Cross-Regulation Advisor Matrix („Map once, comply many“).
 */

import type { BoardReadinessPillarKey } from "@/lib/boardReadinessTypes";

export const ADVISOR_CROSS_REGULATION_VERSION = "wave49-v1";

export const CROSS_REGULATION_PILLAR_ORDER: BoardReadinessPillarKey[] = [
  "eu_ai_act",
  "iso_42001",
  "nis2",
  "dsgvo",
];

/** Kurzbezeichnung im UI (DACH). */
export const CROSS_REGULATION_PILLAR_LABEL_DE: Record<BoardReadinessPillarKey, string> = {
  eu_ai_act: "EU AI Act",
  iso_42001: "ISO 42001",
  nis2: "NIS2 / KRITIS",
  dsgvo: "DSGVO / BDSG",
};

/**
 * Posture-Bucket je Säule (aus Board-Ampel + Lücken-Heuristik).
 * `unknown` = API/Mandant nicht belastbar lesbar.
 */
export type CrossRegulationBucket = "ok" | "needs_attention" | "priority" | "unknown";

export type CrossRegulationMandantRow = {
  tenant_id: string;
  mandant_label: string | null;
  pillars: Record<BoardReadinessPillarKey, CrossRegulationBucket>;
  /** Säulen mit Druck (priority oder needs_attention). */
  active_pillar_pressure_count: number;
  priority_pillar_count: number;
  notes_de: string[];
  links: {
    mandant_export_page: string;
    datev_bundle_api: string;
    readiness_export_api: string;
    board_readiness_admin: string;
  };
};

export type CrossRegulationPillarBucketCounts = Record<CrossRegulationBucket, number>;

export type CrossRegulationPortfolioTotals = {
  per_pillar: Record<BoardReadinessPillarKey, CrossRegulationPillarBucketCounts>;
  /** ≥2 Säulen „priority“. */
  mandanten_multi_pillar_priority: number;
  /** ≥2 Säulen mit priority oder needs_attention. */
  mandanten_multi_pillar_stress: number;
};

export type CrossRegulationTopCase = {
  tenant_id: string;
  mandant_label: string | null;
  hint_de: string;
  links: CrossRegulationMandantRow["links"];
};

export type CrossRegulationMatrixDto = {
  version: typeof ADVISOR_CROSS_REGULATION_VERSION;
  generated_at: string;
  portfolio_generated_at: string;
  disclaimer_de: string;
  totals: CrossRegulationPortfolioTotals;
  mandanten: CrossRegulationMandantRow[];
  top_cases: CrossRegulationTopCase[];
  markdown_de: string;
};
