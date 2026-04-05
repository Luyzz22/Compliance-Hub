/**
 * Wave 47 – SLA-Auswertung aus Portfolio + KPI (ohne server-only, testbar).
 */

import { ADVISOR_SLA_DEFAULT_RULES } from "@/lib/advisorSlaRulesDefault";
import type { AdvisorKpiPortfolioSnapshot } from "@/lib/advisorKpiTypes";
import type { KanzleiAttentionQueueItem, KanzleiPortfolioPayload, KanzleiPortfolioRow } from "@/lib/kanzleiPortfolioTypes";
import type {
  AdvisorEscalationSignalDto,
  AdvisorSlaDeepLinkId,
  AdvisorSlaEvaluationDto,
  AdvisorSlaFindingDto,
  AdvisorSlaMetricKey,
  AdvisorSlaRuleDefinition,
  AdvisorSlaSeverity,
} from "@/lib/advisorSlaTypes";
import { ADVISOR_SLA_VERSION } from "@/lib/advisorSlaTypes";

function rowHasRedPillar(row: KanzleiPortfolioRow): boolean {
  return Object.values(row.pillar_traffic).some((t) => t === "red");
}

function deepLinkForScope(scope: AdvisorSlaRuleDefinition["scope"]): AdvisorSlaDeepLinkId {
  if (scope === "review") return "reviews";
  if (scope === "export") return "exports";
  if (scope === "reminder") return "reminders";
  return "queue";
}

function compare(op: AdvisorSlaRuleDefinition["operator"], left: number, right: number): boolean {
  switch (op) {
    case "lt":
      return left < right;
    case "lte":
      return left <= right;
    case "gt":
      return left > right;
    case "gte":
      return left >= right;
    default:
      return false;
  }
}

function formatPct(x: number): string {
  return `${Math.round(x * 100)} %`;
}

function formatNum(x: number): string {
  return Number.isInteger(x) ? String(x) : x.toFixed(1);
}

export function resolveAdvisorSlaMetricValue(
  key: AdvisorSlaMetricKey,
  payload: KanzleiPortfolioPayload,
  kpi: AdvisorKpiPortfolioSnapshot | null,
): number | null {
  switch (key) {
    case "kpi.review.current_share":
      return kpi?.review.current_share ?? null;
    case "kpi.export.fresh_share":
      return kpi?.export_kpis.fresh_share ?? null;
    case "kpi.hygiene.share_no_red_pillar":
      return kpi?.hygiene.share_no_red_pillar ?? null;
    case "kpi.review.mean_age_days":
      return kpi?.review.mean_age_days ?? null;
    case "payload.open_reminders_total":
      return payload.open_reminders.length;
    case "payload.reminders_overdue_today":
      return payload.reminders_due_today_or_overdue_count;
    case "payload.attention_queue_size":
      return payload.attention_queue.length;
    case "payload.review_stale_mandanten":
      return payload.rows.filter((r) => r.review_stale).length;
    case "payload.never_export_mandanten":
      return payload.rows.filter((r) => r.never_any_export).length;
    case "payload.red_pillar_mandanten":
      return payload.rows.filter((r) => rowHasRedPillar(r)).length;
    default:
      return null;
  }
}

function detailForFinding(
  rule: AdvisorSlaRuleDefinition,
  value: number | null,
  triggered: boolean,
): string {
  if (!triggered || value === null) return "";
  const v = formatNum(value);
  if (rule.metric_key.startsWith("kpi.review.current_share") || rule.metric_key.includes("fresh_share")) {
    return `Ist: ${formatPct(value)} · Schwelle (${rule.operator} ${formatPct(rule.threshold)}).`;
  }
  if (rule.metric_key === "kpi.hygiene.share_no_red_pillar") {
    return `Anteil ohne rote Säule: ${formatPct(value)} · Ziel mindestens ${formatPct(rule.threshold)}.`;
  }
  if (rule.metric_key === "kpi.review.mean_age_days") {
    return `Mittleres Review-Alter ca. ${v} Tage · Schwelle ${rule.operator} ${formatNum(rule.threshold)} Tage.`;
  }
  return `Ist: ${v} · Schwelle ${rule.operator} ${formatNum(rule.threshold)}.`;
}

function buildClientRiskTenants(
  queue: KanzleiAttentionQueueItem[],
  rowsById: Map<string, KanzleiPortfolioRow>,
  maxN: number,
): string[] {
  const out: string[] = [];
  for (const q of queue) {
    const row = rowsById.get(q.tenant_id);
    if (!row) continue;
    if (row.review_stale && rowHasRedPillar(row)) {
      out.push(q.tenant_id);
    }
    if (out.length >= maxN) break;
  }
  return out;
}

export function evaluateAdvisorSla(input: {
  payload: KanzleiPortfolioPayload;
  kpiSnapshot: AdvisorKpiPortfolioSnapshot | null;
  nowMs: number;
  /** Rule-IDs mit Critical beim letzten Lauf (Persistenz). */
  previousCriticalRuleIds: string[];
  rules?: AdvisorSlaRuleDefinition[];
}): AdvisorSlaEvaluationDto {
  const { payload, kpiSnapshot, previousCriticalRuleIds } = input;
  const rules = input.rules ?? ADVISOR_SLA_DEFAULT_RULES;
  const evaluatedAt = new Date(input.nowMs).toISOString();
  const findings: AdvisorSlaFindingDto[] = [];
  const rowsById = new Map(payload.rows.map((r) => [r.tenant_id, r]));

  for (const rule of rules) {
    if (!rule.active) continue;
    const raw = resolveAdvisorSlaMetricValue(rule.metric_key, payload, kpiSnapshot);
    if (raw === null || Number.isNaN(raw)) continue;
    const hit = compare(rule.operator, raw, rule.threshold);
    if (!hit) continue;
    findings.push({
      finding_id: rule.rule_id,
      rule_id: rule.rule_id,
      severity: rule.severity,
      scope: rule.scope,
      title_de: rule.label_de,
      detail_de: detailForFinding(rule, raw, hit),
      deep_link: deepLinkForScope(rule.scope),
    });
  }

  const bySev = (s: AdvisorSlaSeverity) => findings.filter((f) => f.severity === s);
  const critical = bySev("critical");
  const criticalIds = new Set(critical.map((f) => f.rule_id));
  const prev = new Set(previousCriticalRuleIds);
  const persistentCritical = [...criticalIds].filter((id) => prev.has(id));

  const portfolio_red = critical.length >= 2;
  const partner_attention_required =
    critical.length >= 3 || (critical.length >= 1 && persistentCritical.length >= 1);
  const riskTenants = buildClientRiskTenants(payload.attention_queue, rowsById, 6);
  const client_risk_flag = riskTenants.length >= 2;

  const signals: AdvisorEscalationSignalDto[] = [
    {
      signal_id: "portfolio_red",
      active: portfolio_red,
      label_de: "Portfolio kritisch (mehrere SLA-Critical)",
      detail_de:
        portfolio_red && critical.length > 0
          ? `${critical.length} kritische SLA-Verletzungen gleichzeitig – Kanzlei-Partner priorisieren.`
          : "Keine Mehrfach-Critical-Verletzung.",
    },
    {
      signal_id: "partner_attention_required",
      active: partner_attention_required,
      label_de: "Partner-Aufmerksamkeit",
      detail_de:
        partner_attention_required
          ? persistentCritical.length > 0
            ? "Kritische SLA-Verletzungen bestehen fort (Vergleich zum vorherigen Lauf)."
            : "Mehrere kritische Signale – Eskalation mit Partner abstimmen."
          : "Keine fortbestehende Critical-Lage erkannt.",
    },
    {
      signal_id: "client_risk_flag",
      active: client_risk_flag,
      label_de: "Mandanten mit kombiniertem Risiko",
      detail_de:
        client_risk_flag
          ? `${riskTenants.length} Mandanten in der Queue mit überfälligem Review und roter Säule.`
          : "Keine gehäuften Mandanten-Risiken in der Queue.",
      tenant_ids: client_risk_flag ? riskTenants : undefined,
    },
  ];

  const next_steps_de: string[] = [];
  if (findings.some((f) => f.deep_link === "reviews")) {
    next_steps_de.push("Mandanten mit alter Review-Kadenz abarbeiten (Tabelle / Historie).");
  }
  if (findings.some((f) => f.deep_link === "exports")) {
    next_steps_de.push("Readiness- und DATEV-Exporte nachziehen.");
  }
  if (findings.some((f) => f.deep_link === "reminders")) {
    next_steps_de.push("Reminder-Backlog und überfällige Fälligkeiten leeren.");
  }
  if (findings.some((f) => f.deep_link === "queue")) {
    next_steps_de.push("Attention-Queue und kritische Säulen in Board Readiness prüfen.");
  }
  if (next_steps_de.length === 0) {
    next_steps_de.push("Keine SLA-Abweichungen – bestehende Kadenz beibehalten.");
  }

  const activeRules = rules.filter((r) => r.active);
  return {
    version: ADVISOR_SLA_VERSION,
    evaluated_at: evaluatedAt,
    rules_evaluated: activeRules.length,
    findings,
    signals,
    next_steps_de: next_steps_de.slice(0, 5),
  };
}

/** Für Persistenz: aktuelle Critical-Rule-IDs. */
export function criticalRuleIdsFromFindings(findings: AdvisorSlaFindingDto[]): string[] {
  const s = new Set<string>();
  for (const f of findings) {
    if (f.severity === "critical") s.add(f.rule_id);
  }
  return [...s];
}

/** Für Tests und lokale Stubs ohne vollständige SLA-Auswertung. */
export function stubAdvisorSlaEvaluation(evaluatedAtIso: string): AdvisorSlaEvaluationDto {
  return {
    version: ADVISOR_SLA_VERSION,
    evaluated_at: evaluatedAtIso,
    rules_evaluated: 0,
    findings: [],
    signals: [
      {
        signal_id: "portfolio_red",
        active: false,
        label_de: "Portfolio kritisch (mehrere SLA-Critical)",
        detail_de: "Keine Mehrfach-Critical-Verletzung.",
      },
      {
        signal_id: "partner_attention_required",
        active: false,
        label_de: "Partner-Aufmerksamkeit",
        detail_de: "Keine fortbestehende Critical-Lage erkannt.",
      },
      {
        signal_id: "client_risk_flag",
        active: false,
        label_de: "Mandanten mit kombiniertem Risiko",
        detail_de: "Keine gehäuften Mandanten-Risiken in der Queue.",
      },
    ],
    next_steps_de: ["Keine SLA-Abweichungen – bestehende Kadenz beibehalten."],
  };
}
