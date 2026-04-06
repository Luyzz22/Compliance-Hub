/**
 * Wave 48 – AI-Governance-Posture für Advisor-Ansicht (keine Rechtsqualifikation).
 */

import type { BoardReadinessTraffic } from "@/lib/boardReadinessTypes";

export const ADVISOR_AI_GOVERNANCE_VERSION = "wave48-v1";

/** Rohdaten-Hinweis ja / nein / nicht belastbar. */
export type AdvisorAiGovernanceTriState = "yes" | "no" | "unknown";

/** Posture mit Zwischenstufe (z. B. nur Teilmenge der Systeme abgedeckt). */
export type AdvisorAiGovernancePartialTri = "yes" | "no" | "partial";

export type AdvisorAiGovernanceCompletenessBucket = "weak" | "medium" | "strong" | "unknown";

/** Eingangssignale aus Board-Readiness-Snapshot (rein technisch, testbar). */
export type AdvisorAiGovernanceSnapshotInput = {
  tenant_id: string;
  mandant_label: string | null;
  api_fetch_ok: boolean;
  declared_ai_system_count: number;
  has_compliance_dashboard: boolean;
  high_risk_system_count: number;
  eu_ai_act_status: BoardReadinessTraffic;
  eu_ai_act_score: number | null;
  iso_42001_status: BoardReadinessTraffic;
  iso_42001_score: number | null;
  board_report_fresh_when_hr: boolean;
  high_risk_without_owner_count: number;
};

export type AdvisorAiGovernanceMandantRow = {
  tenant_id: string;
  mandant_label: string | null;
  ai_systems_declared: AdvisorAiGovernanceTriState;
  high_risk_indicator: AdvisorAiGovernanceTriState;
  ai_act_artifact_completeness: AdvisorAiGovernanceCompletenessBucket;
  iso42001_governance_completeness: AdvisorAiGovernanceCompletenessBucket;
  post_market_monitoring_readiness: AdvisorAiGovernancePartialTri;
  human_oversight_readiness: AdvisorAiGovernancePartialTri;
  registration_relevance: AdvisorAiGovernanceTriState;
  notes_de: string[];
  links: {
    mandant_export_page: string;
    board_readiness_admin: string;
  };
};

export type AdvisorAiGovernancePortfolioSummary = {
  total_mandanten: number;
  tenants_partial_api: number;
  /** Mandanten mit Hinweis auf mögliche AI-Act-/Register-Thematik (High-Risk im Dashboard). */
  count_likely_ai_act_relevance: number;
  /** High-Risk-Systeme im Compliance-Dashboard erfasst. */
  count_potential_high_risk_exposure: number;
  /** ISO-42001-Säule schwach oder mittel mit rot. */
  count_weak_iso42001: number;
  /** Post-Market/Reporting-Lücke bei vorhandenen HR-Systemen. */
  count_weak_post_market: number;
  /** Prüfbedarf Human Oversight (fehlende Owner bei HR). */
  count_weak_human_oversight: number;
  bucket_ai_act: Record<AdvisorAiGovernanceCompletenessBucket, number>;
  bucket_iso42001: Record<AdvisorAiGovernanceCompletenessBucket, number>;
};

export type AdvisorAiGovernanceTopAttention = {
  tenant_id: string;
  mandant_label: string | null;
  priority_hint_de: string;
  links: AdvisorAiGovernanceMandantRow["links"];
};

export type AdvisorAiGovernancePortfolioDto = {
  version: typeof ADVISOR_AI_GOVERNANCE_VERSION;
  generated_at: string;
  portfolio_generated_at: string;
  disclaimer_de: string;
  summary: AdvisorAiGovernancePortfolioSummary;
  mandanten: AdvisorAiGovernanceMandantRow[];
  top_attention: AdvisorAiGovernanceTopAttention[];
  markdown_de: string;
};
