import React from "react";
import Link from "next/link";

import {
  fetchAIComplianceOverview,
  fetchBoardAlerts,
  fetchBoardKpis,
  fetchBoardAlertsExport,
  getBoardReportDownloadUrl,
  getBoardReportMarkdownDownloadUrl,
  type AIComplianceOverview,
  type AIKpiAlert,
  type BoardKpiSummary,
} from "@/lib/api";
import { BoardToWorkspaceCtas } from "@/components/sbs/BoardToWorkspaceCtas";
import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import {
  BOARD_PAGE_ROOT_CLASS,
  CH_BTN_PRIMARY,
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_CARD_MUTED,
  CH_PAGE_NAV_LINK,
  CH_SECTION_LABEL,
  chKpiStatusFromRatio,
} from "@/lib/boardLayout";

import { KpiExplainButton } from "@/components/ai/KpiExplainButton";

import { BoardKpiAdvisorExport } from "./BoardKpiAdvisorExport";
import { BoardReportAuditSection } from "./BoardReportAuditSection";
import { BoardReportExportForm } from "./BoardReportExportForm";

function scoreColor(score: number): string {
  if (score < 0.4) return "bg-red-50 text-red-800 border-red-100";
  if (score <= 0.7) return "bg-amber-50 text-amber-800 border-amber-100";
  return "bg-emerald-50 text-emerald-800 border-emerald-100";
}

function formatPercent(ratio: number): string {
  return `${Math.round(ratio * 100)}%`;
}

function alertInsightLink(kpiKey: string): { href: string; label: string } {
  if (
    kpiKey === "nis2_incident_readiness_ratio" ||
    kpiKey.includes("incident")
  ) {
    return { href: "/board/incidents", label: "Incident-Ansicht" };
  }
  if (
    kpiKey === "nis2_supplier_risk_coverage_ratio" ||
    kpiKey.includes("supplier")
  ) {
    return { href: "/board/suppliers", label: "Supplier-Risiko" };
  }
  if (
    kpiKey.includes("nis2") ||
    kpiKey.includes("kritis") ||
    kpiKey.includes("ot_it")
  ) {
    return { href: "/board/nis2-kritis", label: "NIS2-Drilldown" };
  }
  if (
    kpiKey.includes("readiness") ||
    kpiKey.includes("eu_ai") ||
    kpiKey.includes("iso42001")
  ) {
    return { href: "/board/eu-ai-act-readiness", label: "EU AI Act Readiness" };
  }
  return { href: "/board/kpis", label: "Board-KPIs" };
}

function ManagementSummary({ kpis }: { kpis: BoardKpiSummary }) {
  const incidentPct = Math.round(kpis.nis2_incident_readiness_ratio * 100);
  const supplierPct = Math.round(kpis.nis2_supplier_risk_coverage_ratio * 100);
  const highRisk = kpis.high_risk_systems;
  const highRiskWithoutDpia = kpis.high_risk_systems_without_dpia;

  const lines: string[] = [];

  if (incidentPct >= 80) {
    lines.push(
      `${incidentPct}% der KI-Systeme sind NIS2-incident-ready (Incident- und Backup-Runbook hinterlegt).`,
    );
  } else if (incidentPct >= 50) {
    lines.push(
      `${incidentPct}% der KI-Systeme sind aktuell NIS2-incident-ready – mittlerer Handlungsbedarf bei Incident- und Backup-Runbooks.`,
    );
  } else {
    lines.push(
      `Nur ${incidentPct}% der KI-Systeme sind NIS2-incident-ready – akuter Handlungsbedarf bei Incident- und Backup-Runbooks.`,
    );
  }

  if (supplierPct >= 80) {
    lines.push(
      `${supplierPct}% der Systeme verfügen über ein gepflegtes Lieferanten-Risikoregister (NIS2 Supply-Chain-Risiko ist weitgehend abgedeckt).`,
    );
  } else if (supplierPct >= 50) {
    lines.push(
      `${supplierPct}% der Systeme haben ein Lieferanten-Risikoregister – weitere Schwerpunkte sollten auf kritischen Lieferanten liegen.`,
    );
  } else {
    lines.push(
      `Nur ${supplierPct}% der Systeme haben ein Lieferanten-Risikoregister – NIS2-Supply-Chain-Risiko ist aktuell unzureichend adressiert.`,
    );
  }

  if (highRisk > 0) {
    const shareWithoutDpia = Math.round((highRiskWithoutDpia / highRisk) * 100);
    lines.push(
      `${highRisk} High-Risk-KI-Systeme sind im Register, davon ${highRiskWithoutDpia} (${shareWithoutDpia}%) noch ohne abgeschlossene DPIA.`,
    );
  } else {
    lines.push("Derzeit sind keine High-Risk-KI-Systeme im Register hinterlegt.");
  }

  return (
    <section
      aria-label="Management-Zusammenfassung AI Governance"
      className={`${CH_CARD_MUTED} mt-8 space-y-2 text-sm text-slate-700`}
    >
      {lines.map((line) => (
        <p key={line}>{line}</p>
      ))}
    </section>
  );
}

function alertSeverityStyles(severity: AIKpiAlert["severity"]): string {
  switch (severity) {
    case "critical":
      return "border-red-200 bg-red-50 text-red-800";
    case "warning":
      return "border-amber-200 bg-amber-50 text-amber-800";
    default:
      return "border-slate-200 bg-slate-50 text-slate-700";
  }
}

function alertSeverityChipClass(severity: AIKpiAlert["severity"]): string {
  switch (severity) {
    case "critical":
      return "bg-red-100 text-red-800 ring-red-200/60";
    case "warning":
      return "bg-amber-100 text-amber-900 ring-amber-200/60";
    default:
      return "bg-slate-100 text-slate-700 ring-slate-200/60";
  }
}

function alertHeadline(alert: AIKpiAlert): string {
  const key = alert.kpi_key;
  if (key.includes("iso42001") || key.includes("iso")) return "ISO 42001 Governance";
  if (key.includes("incident") || key.includes("nis2_incident")) return "NIS2 Incident Readiness";
  if (key.includes("supplier")) return "Supplier Risk";
  if (key.includes("readiness") || key.includes("eu_ai")) return "EU AI Act Readiness";
  if (key.includes("nis2") || key.includes("kritis")) return "NIS2 / KRITIS";
  return "Board-Alert";
}

function KpiStatusChip({ ratio }: { ratio: number | null }) {
  if (ratio == null) {
    return (
      <span className="inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-slate-600 ring-1 ring-slate-200/80">
        Keine Daten
      </span>
    );
  }
  const { label, chipClass } = chKpiStatusFromRatio(ratio);
  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide ring-1 ring-inset ${chipClass}`}
    >
      {label}
    </span>
  );
}

export default async function BoardKpisPage() {
  let kpis: BoardKpiSummary | null = null;
  let complianceOverview: AIComplianceOverview | null = null;
  let alerts: AIKpiAlert[] = [];

  try {
    const [kpisRes, overviewRes, alertsRes] = await Promise.all([
      fetchBoardKpis(),
      fetchAIComplianceOverview(),
      fetchBoardAlerts(),
    ]);
    kpis = kpisRes;
    complianceOverview = overviewRes;
    alerts = alertsRes;
  } catch (error) {
    console.error("Board KPI API error:", error);
  }

  if (!kpis) {
    return (
      <div className={BOARD_PAGE_ROOT_CLASS}>
        <EnterprisePageHeader
          eyebrow="Board"
          title="Board KPIs"
          description="Executive Overview Ihrer AI-Governance – Reifegrad, NIS2 und High-Risk-Register."
        />
        <div
          role="status"
          className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
        >
          KPI-Daten konnten nicht geladen werden. Bitte versuchen Sie es später
          erneut oder wenden Sie sich an das AI-Governance-Team.
        </div>
      </div>
    );
  }

  const isoScore = kpis.iso42001_governance_score;
  const euReadinessRatio = complianceOverview?.overall_readiness ?? null;

  return (
    <div className={BOARD_PAGE_ROOT_CLASS}>
      <EnterprisePageHeader
        eyebrow="Board"
        title="Board KPIs"
        description="Executive Overview Ihrer AI-Governance – ISO 42001, NIS2-Readiness und Lieferanten-Risiko (Standort Deutschland)."
        below={
          <>
            <Link href="/board/nis2-kritis" className={CH_PAGE_NAV_LINK}>
              NIS2 / KRITIS KPI-Drilldown
            </Link>
            <Link href="/board/eu-ai-act-readiness" className={CH_PAGE_NAV_LINK}>
              EU AI Act Readiness
            </Link>
            <Link href="/board/suppliers" className={CH_PAGE_NAV_LINK}>
              Supplier-Risiko
            </Link>
          </>
        }
      />

      <BoardToWorkspaceCtas />

      <section
        aria-label="Executive KPIs"
        className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
      >
        <div
          className={`${CH_CARD} relative flex min-w-0 flex-col border-slate-200/90 ${euReadinessRatio != null ? scoreColor(euReadinessRatio) : "bg-white"}`}
        >
          <div className="flex items-start justify-between gap-2">
            <h2 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-600">
              <span aria-hidden>🤖</span>
              EU AI Act Readiness
            </h2>
            <KpiStatusChip ratio={euReadinessRatio} />
          </div>
          <p className="mt-1 text-xs text-slate-600">
            Gewichtete Erfüllung High-Risk-Anforderungen (Compliance-Overview).
          </p>
          <p className="mt-4 text-4xl font-semibold tabular-nums text-slate-900">
            {euReadinessRatio != null ? formatPercent(euReadinessRatio) : "–"}
          </p>
          <p className="mt-3 flex flex-wrap items-center gap-2">
            <Link
              href="/board/eu-ai-act-readiness"
              className="text-xs font-semibold text-cyan-800 underline decoration-cyan-700/30 hover:text-cyan-950"
            >
              Zur Readiness-Roadmap →
            </Link>
            <KpiExplainButton
              request={{
                kpi_key: "eu_ai_act_readiness",
                current_value:
                  euReadinessRatio != null
                    ? Math.round(euReadinessRatio * 100)
                    : null,
                value_is_percent: true,
                tenant_context: {
                  high_risk_systems_count: kpis.high_risk_systems,
                },
              }}
            />
          </p>
        </div>

        <div className={`${CH_CARD} relative flex min-w-0 flex-col ${scoreColor(kpis.nis2_incident_readiness_ratio)}`}>
          <div className="flex items-start justify-between gap-2">
            <h2 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-600">
              <span aria-hidden>🛡️</span>
              NIS2 Incident Readiness
            </h2>
            <KpiStatusChip ratio={kpis.nis2_incident_readiness_ratio} />
          </div>
          <p className="mt-1 text-xs text-slate-600">
            Anteil Systeme mit Incident- und Backup-Runbook (NIS2/BC).
          </p>
          <p className="mt-4 text-4xl font-semibold tabular-nums text-slate-900">
            {formatPercent(kpis.nis2_incident_readiness_ratio)}
          </p>
          <p className="mt-3 flex flex-wrap items-center gap-2">
            <Link
              href="/board/incidents"
              className="text-xs font-semibold text-cyan-800 underline decoration-cyan-700/30 hover:text-cyan-950"
            >
              Zum Incident-Drilldown →
            </Link>
            <KpiExplainButton
              request={{
                kpi_key: "nis2_incident_readiness_ratio",
                current_value: Math.round(kpis.nis2_incident_readiness_ratio * 100),
                value_is_percent: true,
                tenant_context: {
                  high_risk_systems_count: kpis.high_risk_systems,
                },
              }}
            />
          </p>
        </div>

        <div className={`${CH_CARD} relative flex min-w-0 flex-col ${scoreColor(kpis.nis2_supplier_risk_coverage_ratio)}`}>
          <div className="flex items-start justify-between gap-2">
            <h2 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-600">
              <span aria-hidden>📦</span>
              Supplier Risk Coverage
            </h2>
            <KpiStatusChip ratio={kpis.nis2_supplier_risk_coverage_ratio} />
          </div>
          <p className="mt-1 text-xs text-slate-600">
            Abdeckung Lieferketten-Risiko / Register je KI-System.
          </p>
          <p className="mt-4 text-4xl font-semibold tabular-nums text-slate-900">
            {formatPercent(kpis.nis2_supplier_risk_coverage_ratio)}
          </p>
          <p className="mt-3 flex flex-wrap items-center gap-2">
            <Link
              href="/board/suppliers"
              className="text-xs font-semibold text-cyan-800 underline decoration-cyan-700/30 hover:text-cyan-950"
            >
              Supplier-Drilldown →
            </Link>
            <KpiExplainButton
              request={{
                kpi_key: "nis2_supplier_risk_coverage_ratio",
                current_value: Math.round(kpis.nis2_supplier_risk_coverage_ratio * 100),
                value_is_percent: true,
                tenant_context: {
                  high_risk_systems_count: kpis.high_risk_systems,
                },
              }}
            />
          </p>
        </div>

        <div className={`${CH_CARD} relative flex min-w-0 flex-col ${scoreColor(isoScore)}`}>
          <div className="flex items-start justify-between gap-2">
            <h2 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-600">
              <span aria-hidden>📈</span>
              ISO 42001 Governance
            </h2>
            <KpiStatusChip ratio={isoScore} />
          </div>
          <p className="mt-1 text-xs text-slate-600">
            Reife des AI-Managementsystems (Kontext bis Verbesserung).
          </p>
          <p className="mt-4 text-4xl font-semibold tabular-nums text-slate-900">
            {formatPercent(isoScore)}
          </p>
          <p className="mt-3 flex flex-wrap items-center gap-2">
            <Link
              href="/tenant/eu-ai-act"
              className="text-xs font-semibold text-cyan-800 underline decoration-cyan-700/30 hover:text-cyan-950"
            >
              Tenant-Cockpit →
            </Link>
            <KpiExplainButton
              request={{
                kpi_key: "iso42001_governance_score",
                current_value: Math.round(isoScore * 100),
                value_is_percent: true,
                tenant_context: {
                  high_risk_systems_count: kpis.high_risk_systems,
                },
              }}
            />
          </p>
        </div>
      </section>

      <section
        aria-label="Exporte für Vorstand und Prüfer"
        className={`${CH_CARD} mb-8 border-cyan-100 bg-gradient-to-br from-white to-cyan-50/40`}
      >
        <h2 className={CH_SECTION_LABEL}>Export &amp; Berichte</h2>
        <p className="mt-2 max-w-2xl text-sm text-slate-600">
          Strukturierte Daten für WP, DMS und DATEV-Pipelines – ohne Medienbruch
          in die Nachweisführung.
        </p>
        <div className="mt-5 flex flex-wrap gap-3">
          <a href={fetchBoardAlertsExport("json")} download className={CH_BTN_PRIMARY}>
            Alerts JSON
          </a>
          <a href={fetchBoardAlertsExport("csv")} download className={CH_BTN_SECONDARY}>
            Alerts CSV
          </a>
          <a href={getBoardReportDownloadUrl()} download className={CH_BTN_SECONDARY}>
            Board-Report JSON
          </a>
          <a
            href={getBoardReportMarkdownDownloadUrl()}
            download
            className={CH_BTN_SECONDARY}
          >
            Board-Report Markdown
          </a>
        </div>
        <BoardKpiAdvisorExport />
      </section>

      <section aria-label="Alerts und Hinweise" className={`${CH_CARD} mb-8`}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className={CH_SECTION_LABEL}>Board-Alerts</h2>
          <span className="text-xs text-slate-500">max. 5 Einträge</span>
        </div>
        {alerts.length > 0 ? (
          <ul className="mt-4 space-y-3">
            {alerts.slice(0, 5).map((alert) => {
              const cta = alertInsightLink(alert.kpi_key);
              return (
                <li
                  key={alert.id}
                  className={`rounded-2xl border p-4 shadow-sm ${alertSeverityStyles(alert.severity)}`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-semibold text-slate-900">
                        {alertHeadline(alert)}
                      </p>
                      <p className="mt-1 text-sm leading-relaxed text-slate-700">
                        {alert.message}
                      </p>
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-2 sm:flex-row sm:items-center">
                      <span
                        className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${alertSeverityChipClass(alert.severity)}`}
                      >
                        {alert.severity === "critical"
                          ? "Kritisch"
                          : alert.severity === "warning"
                            ? "Warnung"
                            : "Info"}
                      </span>
                      <Link
                        href={cta.href}
                        className="inline-flex text-xs font-semibold text-slate-900 underline decoration-slate-400 underline-offset-2 hover:text-slate-950"
                      >
                        {cta.label} →
                      </Link>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        ) : (
          <div
            className="mt-6 rounded-2xl border border-dashed border-slate-200 bg-slate-50/80 px-6 py-10 text-center"
            role="status"
          >
            <p className="text-sm font-semibold text-slate-800">Keine aktiven Alerts</p>
            <p className="mt-2 text-sm text-slate-500">
              Schwellenwerte für NIS2, EU AI Act und ISO 42001 sind aktuell nicht
              überschritten. Exporte und Reports bleiben trotzdem verfügbar.
            </p>
          </div>
        )}
      </section>

      {/* KPI Grid */}
      <section
        aria-label="High-Risk-Register"
        className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2"
      >
        {/* High-Risk KI-Systeme gesamt */}
        <div className={`${CH_CARD} flex min-w-0 flex-col`}>
          <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <span aria-hidden>⚠️</span>
            High-Risk KI-Systeme gesamt
          </h3>
          <p className="mt-1 text-xs text-slate-500">
            Anzahl der als High-Risk klassifizierten KI-Systeme.
          </p>
          <div className="mt-4 text-3xl font-semibold text-slate-900">
            {kpis.high_risk_systems}
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Davon {kpis.ai_systems_total} KI-Systeme insgesamt im Register.
          </p>
        </div>

        {/* High-Risk ohne DPIA */}
        <div className={`${CH_CARD} flex min-w-0 flex-col`}>
          <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <span aria-hidden>🔒</span>
            High-Risk ohne DPIA
          </h3>
          <p className="mt-1 text-xs text-slate-500">
            High-Risk-KI-Systeme ohne abgeschlossene Datenschutz-Folgenabschätzung.
          </p>
          <div className="mt-4 text-3xl font-semibold text-slate-900">
            {kpis.high_risk_systems_without_dpia}
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Offene DPIA-Gaps für High-Risk-KI-Systeme gemäß DSGVO.
          </p>
        </div>
      </section>

      {/* EU AI Act / ISO 42001 Readiness */}
      {complianceOverview && (
        <section aria-label="EU AI Act und ISO 42001 Readiness" className={`${CH_CARD} mb-8`}>
          <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-900">
            <span aria-hidden>🤖</span>
            EU AI Act / ISO 42001 Readiness
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Readiness für High-Risk-Anforderungen bis Anwendungsbeginn EU AI Act
            (2. August 2026) und ISO 42001 AI-Managementsystem.
          </p>
          <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="flex min-w-0 flex-col rounded-xl border border-slate-100 bg-slate-50 p-4">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Frist High-Risk
              </h3>
              <p className="mt-2 text-2xl font-semibold text-slate-900">
                {complianceOverview.days_remaining} Tage
              </p>
              <p className="mt-1 text-xs text-slate-500">
                Bis 2. August 2026 (Vollanwendung High-Risk).
              </p>
            </div>
            <div className="flex min-w-0 flex-col rounded-xl border border-slate-100 bg-slate-50 p-4">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                High-Risk voll kontrolliert
              </h3>
              <p className="mt-2 text-2xl font-semibold text-slate-900">
                {complianceOverview.high_risk_systems_with_full_controls}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                Systeme mit vollständig erfüllten Anforderungen.
              </p>
            </div>
            <div className="flex min-w-0 flex-col rounded-xl border border-slate-100 bg-slate-50 p-4">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                High-Risk mit kritischen Lücken
              </h3>
              <p className="mt-2 text-2xl font-semibold text-slate-900">
                {complianceOverview.high_risk_systems_with_critical_gaps}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                Systeme mit offenen Anforderungen (nicht begonnen).
              </p>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="flex min-w-0 flex-col rounded-xl border border-indigo-100 bg-indigo-50/80 p-4">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-indigo-800">
                NIS2 / KRITIS KPI (Mittelwert)
              </h3>
              <p className="mt-2 text-2xl font-semibold text-indigo-950">
                {complianceOverview.nis2_kritis_kpi_mean_percent != null
                  ? `${Math.round(complianceOverview.nis2_kritis_kpi_mean_percent)} %`
                  : "–"}
              </p>
              <p className="mt-1 text-xs text-indigo-900/80">
                Durchschnitt aller gepflegten Incident-/Supplier-/OT-IT-KPIs (0–100).
              </p>
            </div>
            <div className="flex min-w-0 flex-col rounded-xl border border-indigo-100 bg-indigo-50/80 p-4">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-indigo-800">
                NIS2 / KRITIS KPI-Abdeckung
              </h3>
              <p className="mt-2 text-2xl font-semibold text-indigo-950">
                {formatPercent(
                  complianceOverview.nis2_kritis_systems_full_coverage_ratio ?? 0,
                )}
              </p>
              <p className="mt-1 text-xs text-indigo-900/80">
                Anteil KI-Systeme mit allen drei KPI-Typen befüllt.
              </p>
            </div>
          </div>
          {complianceOverview.top_critical_requirements.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-semibold text-slate-700">
                Top kritische Anforderungen (betroffene Systeme)
              </h3>
              <ul className="mt-2 space-y-1.5 text-sm text-slate-600">
                {complianceOverview.top_critical_requirements.map((req, i) => (
                  <li key={i} className="flex min-w-0 justify-between gap-4">
                    <span className="min-w-0">
                      <strong className="text-slate-800">{req.article}</strong>{" "}
                      {req.name}
                    </span>
                    <span className="font-medium text-slate-700">
                      {req.affected_systems_count} System
                      {req.affected_systems_count !== 1 ? "e" : ""}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <p className="mt-4">
            <Link
              href="/tenant/eu-ai-act"
              className="text-sm font-medium text-slate-600 underline hover:text-slate-900"
              aria-label="EU AI Act Tenant-Details öffnen"
            >
              Details anzeigen
            </Link>
          </p>
        </section>
      )}

      {/* Externer Export (Webhook / DMS / SAP BTP) */}
      <section className="mb-8">
        <BoardReportExportForm />
      </section>

      {/* Audit-Ready (Prüfungsdokumentation) */}
      <section className="mb-8">
        <BoardReportAuditSection />
      </section>

      <ManagementSummary kpis={kpis} />
    </div>
  );
}

