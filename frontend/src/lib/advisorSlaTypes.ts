/**
 * Wave 47 – Leichte SLA-Regeln & Eskalationssignale (intern, kein Workflow-Engine).
 */

export type AdvisorSlaScope = "review" | "export" | "reminder" | "gaps";

export const ADVISOR_SLA_VERSION = "wave47-v1";

export type AdvisorSlaConditionType = "threshold_kpi" | "threshold_age" | "threshold_count";

export type AdvisorSlaSeverity = "info" | "warning" | "critical";

/** Mandanten-Workspace der Kanzlei; `null` = gilt für das aktuelle Advisor-Portfolio. */
export type AdvisorSlaTenantScope = string | null;

export type AdvisorSlaMetricKey =
  | "kpi.review.current_share"
  | "kpi.export.fresh_share"
  | "kpi.hygiene.share_no_red_pillar"
  | "kpi.review.mean_age_days"
  | "payload.open_reminders_total"
  | "payload.reminders_overdue_today"
  | "payload.attention_queue_size"
  | "payload.review_stale_mandanten"
  | "payload.never_export_mandanten"
  | "payload.red_pillar_mandanten";

export type AdvisorSlaOperator = "lt" | "lte" | "gt" | "gte";

/** Regel-Definition (konfigurierbar; Standard siehe advisorSlaRulesDefault). */
export type AdvisorSlaRuleDefinition = {
  rule_id: string;
  tenant_id: AdvisorSlaTenantScope;
  scope: AdvisorSlaScope;
  condition_type: AdvisorSlaConditionType;
  metric_key: AdvisorSlaMetricKey;
  operator: AdvisorSlaOperator;
  threshold: number;
  severity: AdvisorSlaSeverity;
  active: boolean;
  /** kpi.review.current_share → „Review-Deckung“ */
  label_de: string;
};

export type AdvisorSlaDeepLinkId = "reviews" | "exports" | "reminders" | "gaps" | "queue";

export type AdvisorSlaFindingDto = {
  finding_id: string;
  rule_id: string;
  severity: AdvisorSlaSeverity;
  scope: AdvisorSlaScope;
  title_de: string;
  detail_de: string;
  deep_link: AdvisorSlaDeepLinkId;
};

export type AdvisorEscalationSignalId = "portfolio_red" | "partner_attention_required" | "client_risk_flag";

export type AdvisorEscalationSignalDto = {
  signal_id: AdvisorEscalationSignalId;
  active: boolean;
  label_de: string;
  detail_de: string;
  tenant_ids?: string[];
};

export type AdvisorSlaEvaluationDto = {
  version: typeof ADVISOR_SLA_VERSION;
  evaluated_at: string;
  rules_evaluated: number;
  findings: AdvisorSlaFindingDto[];
  signals: AdvisorEscalationSignalDto[];
  /** Kurze Handlungsimpulse für Cockpit/Reports. */
  next_steps_de: string[];
};
