/**
 * Wave 44 – Kanzlei Partner-Review-Paket (Portfolio-Steuerung, kein Board-Pack).
 */

import type { AdvisorKpiTrendsNarrativeBlock } from "@/lib/advisorKpiTrendsBuild";
import type { AdvisorKpiPortfolioSnapshot } from "@/lib/advisorKpiTypes";
import type { AdvisorAiGovernancePortfolioDto } from "@/lib/advisorAiGovernanceTypes";
import type { AdvisorSlaEvaluationDto } from "@/lib/advisorSlaTypes";
import type { GtmReadinessClass } from "@/lib/gtmAccountReadiness";
import type { KanzleiMonthlyChangeLine } from "@/lib/kanzleiMonthlyReportTypes";

export const PARTNER_REVIEW_PACKAGE_VERSION = "wave48-v1";

export type PartnerReviewPackageMeta = {
  version: typeof PARTNER_REVIEW_PACKAGE_VERSION;
  generated_at: string;
  portfolio_version: string;
  portfolio_generated_at: string;
  compared_to_baseline: boolean;
  baseline_saved_at: string | null;
  baseline_period_label: string | null;
  attention_top_n: number;
  /** Kurz erklärt, welche Heuristiken das Paket nutzt (für Partner-Transparenz). */
  prioritization_rationale_de: string[];
};

export type PartnerReviewPartA = {
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
  attention_queue_size: number;
  open_reminders_open_count: number;
  reminders_due_today_or_overdue_count: number;
  reminders_due_this_week_open_count: number;
};

export type PartnerReviewAttentionEntry = {
  rank: number;
  tenant_id: string;
  mandant_label: string | null;
  attention_score: number;
  warum_jetzt_de: string[];
  naechster_schritt_de: string;
};

export type PartnerReviewPartC = {
  baseline_available: boolean;
  baseline_saved_at: string | null;
  baseline_period_label: string | null;
  improvements: KanzleiMonthlyChangeLine[];
  deteriorations: KanzleiMonthlyChangeLine[];
  newly_urgent: KanzleiMonthlyChangeLine[];
};

export type PartnerReviewPackageDto = {
  meta: PartnerReviewPackageMeta;
  part_a_portfolio_overview: PartnerReviewPartA;
  part_b_top_attention: PartnerReviewAttentionEntry[];
  part_c_changes_since_baseline: PartnerReviewPartC;
  part_d_recommended_priorities_de: string[];
  /** Wave 45 – gleicher Snapshot wie Monatsreport-KPI-Block. */
  part_e_advisor_kpis: AdvisorKpiPortfolioSnapshot | null;
  /** Wave 46 – KPI-Trend-Kurzsätze (rolling History). */
  part_f_kpi_trends: AdvisorKpiTrendsNarrativeBlock | null;
  /** Wave 47 – SLA-Lagebild (Befunde + Eskalation). */
  part_g_sla_lagebild: AdvisorSlaEvaluationDto;
  /** Wave 48 – AI-Governance-Steuerung (EU AI Act / ISO 42001). */
  part_h_ai_governance: AdvisorAiGovernancePortfolioDto;
};
