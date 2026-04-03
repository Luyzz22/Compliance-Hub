import type { GtmDashboardSnapshot } from "@/lib/gtmDashboardTypes";

import {
  GTM_ALERT_DEAD_LETTER_CRITICAL,
  GTM_ALERT_DEAD_LETTER_WARNING,
  GTM_ALERT_QUAL_NO_DEAL_CRITICAL,
  GTM_ALERT_QUAL_NO_DEAL_WARNING,
  GTM_ALERT_UNTRIAGED_CRITICAL,
  GTM_ALERT_UNTRIAGED_WARNING,
} from "@/lib/gtmAlertThresholds";

export type GtmAlertSeverity = "warning" | "critical";

export type GtmAlertFinding = {
  id: string;
  severity: GtmAlertSeverity;
  message_de: string;
};

export function evaluateGtmAlertsFromSnapshot(snapshot: GtmDashboardSnapshot): GtmAlertFinding[] {
  const c = snapshot.health_signal_counts;
  const findings: GtmAlertFinding[] = [];

  if (c.untriaged_over_3d >= GTM_ALERT_UNTRIAGED_CRITICAL) {
    findings.push({
      id: "untriaged_backlog_critical",
      severity: "critical",
      message_de: `${c.untriaged_over_3d} Leads „Neu“ älter als 3 Tage — Triage-Rückstand kritisch.`,
    });
  } else if (c.untriaged_over_3d >= GTM_ALERT_UNTRIAGED_WARNING) {
    findings.push({
      id: "untriaged_backlog_warning",
      severity: "warning",
      message_de: `${c.untriaged_over_3d} Leads „Neu“ älter als 3 Tage — Triage prüfen.`,
    });
  }

  if (c.crm_dead_letter_30d >= GTM_ALERT_DEAD_LETTER_CRITICAL) {
    findings.push({
      id: "dead_letter_critical",
      severity: "critical",
      message_de: `${c.crm_dead_letter_30d} CRM Dead Letters (30 Tage) — Sync/Downstream dringend.`,
    });
  } else if (c.crm_dead_letter_30d >= GTM_ALERT_DEAD_LETTER_WARNING) {
    findings.push({
      id: "dead_letter_warning",
      severity: "warning",
      message_de: `${c.crm_dead_letter_30d} CRM Dead Letters (30 Tage) — Jobs ansehen.`,
    });
  }

  if (c.qualified_no_pipedrive_deal_old_7d >= GTM_ALERT_QUAL_NO_DEAL_CRITICAL) {
    findings.push({
      id: "qualified_no_deal_critical",
      severity: "critical",
      message_de: `${c.qualified_no_pipedrive_deal_old_7d} qualifizierte Leads ohne Deal (Proxy >7d) — Pipeline-Übergang.`,
    });
  } else if (c.qualified_no_pipedrive_deal_old_7d >= GTM_ALERT_QUAL_NO_DEAL_WARNING) {
    findings.push({
      id: "qualified_no_deal_warning",
      severity: "warning",
      message_de: `${c.qualified_no_pipedrive_deal_old_7d} qualifizierte Leads ohne Deal (Proxy) — prüfen.`,
    });
  }

  return findings;
}
