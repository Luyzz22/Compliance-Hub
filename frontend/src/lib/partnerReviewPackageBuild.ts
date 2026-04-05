/**
 * Wave 44 – Partner-Review-Paket aus Portfolio + Monats-Baseline (ohne server-only).
 */

import type { KanzleiMonthlyBaselineTenant } from "@/lib/kanzleiMonthlyReportTypes";
import {
  buildKanzleiMonthlyReportSection3,
  buildKanzleiPortfolioFocusAreasDe,
  summarizeKanzleiMonthlyReportSection1,
} from "@/lib/kanzleiMonthlyReportBuild";
import type { AdvisorKpiTrendsNarrativeBlock } from "@/lib/advisorKpiTrendsBuild";
import type { AdvisorKpiPortfolioSnapshot } from "@/lib/advisorKpiTypes";
import type { KanzleiPortfolioPayload } from "@/lib/kanzleiPortfolioTypes";
import type {
  PartnerReviewAttentionEntry,
  PartnerReviewPackageDto,
  PartnerReviewPartA,
  PartnerReviewPartC,
} from "@/lib/partnerReviewPackageTypes";
import { PARTNER_REVIEW_PACKAGE_VERSION } from "@/lib/partnerReviewPackageTypes";

const CAP_IMPROVE = 10;
const CAP_DETERIORATE = 10;
const CAP_URGENT = 12;

/** Heuristiken in Kurzform – identisch zur Doku `wave44-partner-review-package.md`. */
export function partnerReviewPrioritizationRationaleDe(): string[] {
  return [
    "Überfälliges oder fehlendes Kanzlei-Review (Review-Kadenz) erhöht Dringlichkeit in Queue und Remindern.",
    "Export-Kadenz (Readiness-Export / DATEV-ZIP) und „nie exportiert“ sind harte Steuerungssignale.",
    "Viele offene Prüfpunkte und hohe Dringlichkeit (Hoch) ziehen Attention-Score und Fokus-Säule.",
    "Rote Säulen-Ampeln (EU AI Act, ISO 42001, NIS2, DSGVO) qualifizieren für Queue und Partner-Fokus.",
    "Offene Reminder mit Fälligkeit heute oder überfällig werden im Paket-Überblick hervorgehoben.",
    "Attention-Queue sortiert nach Score, offenen Punkten und Mandantenbezeichnung – keine Ticket-Engine.",
  ];
}

function mergePartC(
  s3: ReturnType<typeof buildKanzleiMonthlyReportSection3>,
): PartnerReviewPartC {
  const improvements = [
    ...s3.readiness_improved,
    ...s3.open_points_decreased,
    ...s3.attention_eased,
  ].slice(0, CAP_IMPROVE);

  const deteriorations = [
    ...s3.readiness_deteriorated,
    ...s3.open_points_increased,
  ].slice(0, CAP_DETERIORATE);

  const newly_urgent = [...s3.attention_escalated, ...s3.cadence_notes].slice(0, CAP_URGENT);

  return {
    baseline_available: s3.baseline_available,
    baseline_saved_at: s3.baseline_saved_at,
    baseline_period_label: s3.baseline_period_label,
    improvements,
    deteriorations,
    newly_urgent,
  };
}

function buildPartA(payload: KanzleiPortfolioPayload): PartnerReviewPartA {
  const s1 = summarizeKanzleiMonthlyReportSection1(payload);
  return {
    total_mandanten: s1.total_mandanten,
    tenants_partial_api: s1.tenants_partial_api,
    backend_reachable: s1.backend_reachable,
    readiness_distribution: s1.readiness_distribution,
    count_review_stale: s1.count_review_stale,
    count_export_stale: s1.count_export_stale,
    count_board_report_stale: s1.count_board_report_stale,
    count_never_export: s1.count_never_export,
    total_open_points: s1.total_open_points,
    total_open_points_hoch: s1.total_open_points_hoch,
    attention_queue_size: s1.count_queue,
    open_reminders_open_count: payload.open_reminders.length,
    reminders_due_today_or_overdue_count: payload.reminders_due_today_or_overdue_count,
    reminders_due_this_week_open_count: payload.reminders_due_this_week_open_count,
  };
}

function buildPartB(
  payload: KanzleiPortfolioPayload,
  topN: number,
): PartnerReviewAttentionEntry[] {
  const n = Math.min(15, Math.max(3, topN));
  return payload.attention_queue.slice(0, n).map((q, i) => ({
    rank: i + 1,
    tenant_id: q.tenant_id,
    mandant_label: q.mandant_label,
    attention_score: q.attention_score,
    warum_jetzt_de: q.warum_jetzt_de,
    naechster_schritt_de: q.naechster_schritt_de,
  }));
}

export type BuildPartnerReviewPackageOptions = {
  compareToBaseline: boolean;
  attentionTopN: number;
  generatedAt?: Date;
  /** Wave 45 – Kanzlei-KPIs (optional). */
  advisorKpiSnapshot?: AdvisorKpiPortfolioSnapshot | null;
  /** Wave 46 – KPI-Trends (optional). */
  kpiTrendsNarrative?: AdvisorKpiTrendsNarrativeBlock | null;
};

export function buildPartnerReviewPackage(
  payload: KanzleiPortfolioPayload,
  baseline: {
    saved_at: string;
    period_label: string | null;
    tenants: Record<string, KanzleiMonthlyBaselineTenant>;
  } | null,
  opts: BuildPartnerReviewPackageOptions,
): PartnerReviewPackageDto {
  const generatedAt = opts.generatedAt ?? new Date();
  const s1 = summarizeKanzleiMonthlyReportSection1(payload);
  const s3 = opts.compareToBaseline
    ? buildKanzleiMonthlyReportSection3(payload, baseline)
    : {
        baseline_available: false,
        baseline_saved_at: baseline?.saved_at ?? null,
        baseline_period_label: baseline?.period_label ?? null,
        readiness_improved: [],
        readiness_deteriorated: [],
        open_points_increased: [],
        open_points_decreased: [],
        attention_escalated: [],
        attention_eased: [],
        cadence_notes: [],
      };

  const compared =
    opts.compareToBaseline && Boolean(baseline && Object.keys(baseline.tenants).length > 0);

  const part_d = buildKanzleiPortfolioFocusAreasDe(payload, s1);

  return {
    meta: {
      version: PARTNER_REVIEW_PACKAGE_VERSION,
      generated_at: generatedAt.toISOString(),
      portfolio_version: payload.version,
      portfolio_generated_at: payload.generated_at,
      compared_to_baseline: compared,
      baseline_saved_at: baseline?.saved_at ?? null,
      baseline_period_label: baseline?.period_label ?? null,
      attention_top_n: Math.min(15, Math.max(3, opts.attentionTopN)),
      prioritization_rationale_de: partnerReviewPrioritizationRationaleDe(),
    },
    part_a_portfolio_overview: buildPartA(payload),
    part_b_top_attention: buildPartB(payload, opts.attentionTopN),
    part_c_changes_since_baseline: mergePartC(s3),
    part_d_recommended_priorities_de: part_d.slice(0, 8),
    part_e_advisor_kpis: opts.advisorKpiSnapshot ?? null,
    part_f_kpi_trends: opts.kpiTrendsNarrative ?? null,
    part_g_sla_lagebild: payload.advisor_sla,
  };
}
