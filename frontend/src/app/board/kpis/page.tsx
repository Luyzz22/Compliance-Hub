import React from "react";
import Link from "next/link";

import {
  fetchAIComplianceOverview,
  fetchBoardAlerts,
  fetchBoardKpis,
  fetchBoardAlertsExport,
  type AIComplianceOverview,
  type AIKpiAlert,
  type BoardKpiSummary,
} from "@/lib/api";

function scoreColor(score: number): string {
  if (score < 0.4) return "bg-red-50 text-red-800 border-red-100";
  if (score <= 0.7) return "bg-amber-50 text-amber-800 border-amber-100";
  return "bg-emerald-50 text-emerald-800 border-emerald-100";
}

function formatPercent(ratio: number): string {
  return `${Math.round(ratio * 100)}%`;
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
      className="mt-8 space-y-1 rounded-xl border border-slate-100 bg-slate-50 p-4 text-sm text-slate-700"
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
      <main className="mx-auto max-w-6xl px-4 py-8">
        <header className="mb-6">
          <h1 className="text-2xl font-bold text-slate-900">
            AI Governance – Board KPIs
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Überblick über Reifegrad, NIS2-Readiness und High-Risk-KI-Systeme.
          </p>
        </header>
        <div
          role="status"
          className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800"
        >
          KPI-Daten konnten nicht geladen werden. Bitte versuchen Sie es später
          erneut oder wenden Sie sich an das AI-Governance-Team.
        </div>
      </main>
    );
  }

  const isoScore = kpis.iso42001_governance_score;

  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">
          AI Governance – Board KPIs
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          ISO 42001 Reifegrad, NIS2-Incident-Readiness und Lieferanten-Risiko im
          Überblick für den Standort Deutschland.
        </p>
      </header>

      {/* Alerts & Hinweise (max 5) + Export für CISO/ISB/Vorstand */}
      <section
        aria-label="Alerts und Hinweise"
        className="mb-6 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
      >
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-600">
          Alerts &amp; Hinweise
        </h2>
        {alerts.length > 0 ? (
          <ul className="mt-3 space-y-2">
            {alerts.slice(0, 5).map((alert) => (
              <li
                key={alert.id}
                className={`rounded-lg border px-3 py-2 text-sm ${alertSeverityStyles(alert.severity)}`}
              >
                {alert.message}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-sm text-slate-500">
            Keine aktuellen Alerts.
          </p>
        )}
        <p className="mt-4 text-xs text-slate-600">
          Für Weiterleitung an CISO / ISB / Vorstand:{" "}
          <a
            href={fetchBoardAlertsExport("json")}
            download
            className="font-medium text-slate-800 underline hover:text-slate-600"
          >
            Alerts als JSON exportieren
          </a>
          {" · "}
          <a
            href={fetchBoardAlertsExport("csv")}
            download
            className="font-medium text-slate-800 underline hover:text-slate-600"
          >
            Alerts als CSV exportieren
          </a>
        </p>
      </section>

      {/* Hero: ISO 42001 Governance Score */}
      {(() => {
        const hasCriticalForIso = alerts.some(
          (a) => a.severity === "critical" && a.kpi_key === "iso42001_governance_score",
        );
        return (
          <section
            aria-label="AI-Governance-Reife nach ISO 42001"
            className={`relative mb-8 flex flex-col justify-between gap-4 rounded-2xl border p-6 shadow-sm ${scoreColor(
              isoScore,
            )} ${hasCriticalForIso ? "ring-2 ring-red-300" : ""}`}
          >
            {hasCriticalForIso && (
              <span
                className="absolute right-4 top-4 h-2.5 w-2.5 rounded-full bg-red-500"
                aria-hidden
              />
            )}
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-wide">
                AI-Governance-Reife (ISO 42001)
              </h2>
          <p className="mt-1 text-xs text-slate-700">
            Aggregierter Reifegrad des AI-Managementsystems (Kontext, Führung,
            Risikobewertung, Betrieb, Verbesserung).
          </p>
        </div>
        <div className="flex items-baseline gap-3">
          <span className="text-5xl font-semibold leading-none">
            {formatPercent(isoScore)}
          </span>
          <span className="text-sm font-medium text-slate-700">
            von 100&nbsp;% Zielreife
          </span>
        </div>
      </section>
        );
      })()}

      {/* KPI Grid */}
      <section
        aria-label="NIS2- und High-Risk-KPIs"
        className="mb-4 grid gap-4 md:grid-cols-2 lg:grid-cols-4"
      >
        {/* NIS2 Incident Readiness */}
        {(() => {
          const hasCritical = alerts.some(
            (a) =>
              a.severity === "critical" &&
              a.kpi_key === "nis2_incident_readiness_ratio",
          );
          return (
            <div
              className={`relative flex flex-col rounded-xl border border-slate-100 bg-white p-4 shadow-sm ${hasCritical ? "ring-2 ring-red-300" : ""}`}
            >
              {hasCritical && (
                <span
                  className="absolute right-3 top-3 h-2 w-2 rounded-full bg-red-500"
                  aria-hidden
                />
              )}
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                NIS2 Incident Readiness
              </h3>
          <p className="mt-1 text-xs text-slate-500">
            Anteil KI-Systeme mit Incident- und Backup-Runbook.
          </p>
          <div className="mt-4 text-3xl font-semibold text-slate-900">
            {formatPercent(kpis.nis2_incident_readiness_ratio)}
          </div>
          <p className="mt-1 text-xs text-slate-500">
            {formatPercent(kpis.nis2_incident_readiness_ratio)} der
            KI-Systeme mit Incident- &amp; Backup-Runbook.
          </p>
          <p className="mt-3">
            <Link
              href="/board/incidents"
              className="text-xs font-medium text-slate-600 underline hover:text-slate-900"
              aria-label="Incident-Drilldown öffnen"
            >
              Incident-Details anzeigen
            </Link>
          </p>
            </div>
          );
        })()}

        {/* NIS2 Supplier Risk Coverage */}
        {(() => {
          const hasCritical = alerts.some(
            (a) =>
              a.severity === "critical" &&
              a.kpi_key === "nis2_supplier_risk_coverage_ratio",
          );
          return (
            <div
              className={`relative flex flex-col rounded-xl border border-slate-100 bg-white p-4 shadow-sm ${hasCritical ? "ring-2 ring-red-300" : ""}`}
            >
              {hasCritical && (
                <span
                  className="absolute right-3 top-3 h-2 w-2 rounded-full bg-red-500"
                  aria-hidden
                />
              )}
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                NIS2 Supplier Risk Coverage
              </h3>
          <p className="mt-1 text-xs text-slate-500">
            Anteil KI-Systeme mit dokumentiertem Lieferanten-Risikoregister.
          </p>
          <div className="mt-4 text-3xl font-semibold text-slate-900">
            {formatPercent(kpis.nis2_supplier_risk_coverage_ratio)}
          </div>
          <p className="mt-1 text-xs text-slate-500">
            {formatPercent(kpis.nis2_supplier_risk_coverage_ratio)} der Systeme
            mit Supplier-Risikoregister.
          </p>
          <p className="mt-3">
            <Link
              href="/board/suppliers"
              className="text-xs font-medium text-slate-600 underline hover:text-slate-900"
              aria-label="Supplier-Risiko-Drilldown öffnen"
            >
              Details anzeigen
            </Link>
          </p>
            </div>
          );
        })()}

        {/* High-Risk KI-Systeme gesamt */}
        <div className="flex flex-col rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
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
        <div className="flex flex-col rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
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
        <section
          aria-label="EU AI Act und ISO 42001 Readiness"
          className="mb-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
        >
          <h2 className="text-lg font-semibold text-slate-900">
            EU AI Act / ISO 42001 Readiness
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Readiness für High-Risk-Anforderungen bis Anwendungsbeginn EU AI Act
            (2. August 2026) und ISO 42001 AI-Managementsystem.
          </p>
          <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div
              className={`flex flex-col rounded-xl border p-4 ${scoreColor(
                complianceOverview.overall_readiness,
              )}`}
            >
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                Gesamt-Readiness
              </h3>
              <p className="mt-2 text-3xl font-semibold">
                {formatPercent(complianceOverview.overall_readiness)}
              </p>
              <p className="mt-1 text-xs text-slate-600">
                EU AI Act &amp; ISO 42001 Anforderungen gewichtet.
              </p>
            </div>
            <div className="flex flex-col rounded-xl border border-slate-100 bg-slate-50 p-4">
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
            <div className="flex flex-col rounded-xl border border-slate-100 bg-slate-50 p-4">
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
            <div className="flex flex-col rounded-xl border border-slate-100 bg-slate-50 p-4">
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
          {complianceOverview.top_critical_requirements.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-semibold text-slate-700">
                Top kritische Anforderungen (betroffene Systeme)
              </h3>
              <ul className="mt-2 space-y-1.5 text-sm text-slate-600">
                {complianceOverview.top_critical_requirements.map((req, i) => (
                  <li key={i} className="flex justify-between gap-4">
                    <span>
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

      <ManagementSummary kpis={kpis} />
    </main>
  );
}

