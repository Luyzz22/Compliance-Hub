/**
 * Wave 42–45 – Kanzlei-Monatsreport / Sammelreport (Portfolio-Ebene, kein Board-Pack).
 */

import type { AdvisorKpiTrendsNarrativeBlock } from "@/lib/advisorKpiTrendsBuild";
import type { AdvisorKpiPortfolioSnapshot } from "@/lib/advisorKpiTypes";
import type { AdvisorAiGovernancePortfolioDto } from "@/lib/advisorAiGovernanceTypes";
import type { CrossRegulationMatrixDto } from "@/lib/advisorCrossRegulationTypes";
import type { AdvisorSlaEvaluationDto } from "@/lib/advisorSlaTypes";
import type { BoardReadinessPillarKey, BoardReadinessTraffic } from "@/lib/boardReadinessTypes";
import type { GtmReadinessClass } from "@/lib/gtmAccountReadiness";

export const KANZLEI_MONTHLY_REPORT_VERSION = "wave49-v1";

export type KanzleiAttentionBand = "low" | "medium" | "high";

/** Pro Mandant für Vergleich (persistiert in Baseline-Datei). */
export type KanzleiMonthlyBaselineTenant = {
  readiness_class: GtmReadinessClass;
  attention_score: number;
  attention_band: KanzleiAttentionBand;
  open_points_count: number;
  open_points_hoch: number;
  worst_traffic: BoardReadinessTraffic;
  review_stale: boolean;
  any_export_stale: boolean;
  board_report_stale: boolean;
  pillar_traffic: Record<BoardReadinessPillarKey, BoardReadinessTraffic>;
};

export type KanzleiMonthlyReportBaselineState = {
  saved_at: string;
  period_label: string | null;
  portfolio_generated_at: string | null;
  tenants: Record<string, KanzleiMonthlyBaselineTenant>;
};

export type KanzleiMonthlyChangeLine = {
  tenant_id: string;
  mandant_label: string | null;
  text_de: string;
};

export type KanzleiMonthlyReportSection1 = {
  total_mandanten: number;
  tenants_partial_api: number;
  backend_reachable: boolean;
  readiness_distribution: Record<GtmReadinessClass, number>;
  count_review_stale: number;
  count_export_stale: number;
  count_board_report_stale: number;
  count_never_export: number;
  total_open_points: number;
  total_open_points_hoch: number;
  count_queue: number;
};

export type KanzleiMonthlyReportAttentionRow = {
  rank: number;
  tenant_id: string;
  mandant_label: string | null;
  attention_score: number;
  naechster_schritt_de: string;
};

export type KanzleiMonthlyReportSection3 = {
  baseline_available: boolean;
  baseline_saved_at: string | null;
  baseline_period_label: string | null;
  readiness_improved: KanzleiMonthlyChangeLine[];
  readiness_deteriorated: KanzleiMonthlyChangeLine[];
  open_points_increased: KanzleiMonthlyChangeLine[];
  open_points_decreased: KanzleiMonthlyChangeLine[];
  attention_escalated: KanzleiMonthlyChangeLine[];
  attention_eased: KanzleiMonthlyChangeLine[];
  cadence_notes: KanzleiMonthlyChangeLine[];
};

export type KanzleiMonthlyReportDto = {
  version: typeof KANZLEI_MONTHLY_REPORT_VERSION;
  generated_at: string;
  period_label: string;
  portfolio_version: string;
  portfolio_generated_at: string;
  compared_to_baseline: boolean;
  section_1_portfolio_summary: KanzleiMonthlyReportSection1;
  section_2_attention_top: KanzleiMonthlyReportAttentionRow[];
  section_3_changes: KanzleiMonthlyReportSection3;
  section_4_focus_areas_de: string[];
  /** Wave 45 – Kanzlei-KPI-Snapshot; null wenn nicht mitgeliefert. */
  section_5_advisor_kpis: AdvisorKpiPortfolioSnapshot | null;
  /** Wave 46 – Kurz-Trends aus persistierter KPI-History (rolling, kein BI). */
  section_6_kpi_trends: AdvisorKpiTrendsNarrativeBlock | null;
  /** Wave 47 – SLA-Befunde und Eskalationssignale (aus Portfolio-Compute). */
  section_7_advisor_sla: AdvisorSlaEvaluationDto;
  /** Wave 48 – AI-Governance-Posture (EU AI Act / ISO 42001, heuristisch). */
  section_8_ai_governance: AdvisorAiGovernancePortfolioDto;
  /** Wave 49 – Cross-Regulation-Matrix (vier Säulen). */
  section_9_cross_regulation_matrix: CrossRegulationMatrixDto;
};
