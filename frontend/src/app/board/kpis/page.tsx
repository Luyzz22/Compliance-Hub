import React from "react";
import Link from "next/link";

import { fetchBoardKpis, type BoardKpiSummary } from "@/lib/api";

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

export default async function BoardKpisPage() {
  let kpis: BoardKpiSummary | null = null;

  try {
    kpis = await fetchBoardKpis();
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

      {/* Hero: ISO 42001 Governance Score */}
      <section
        aria-label="AI-Governance-Reife nach ISO 42001"
        className={`mb-8 flex flex-col justify-between gap-4 rounded-2xl border p-6 shadow-sm ${scoreColor(
          isoScore,
        )}`}
      >
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

      {/* KPI Grid */}
      <section
        aria-label="NIS2- und High-Risk-KPIs"
        className="mb-4 grid gap-4 md:grid-cols-2 lg:grid-cols-4"
      >
        {/* NIS2 Incident Readiness */}
        <div className="flex flex-col rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
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

        {/* NIS2 Supplier Risk Coverage */}
        <div className="flex flex-col rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
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
        </div>

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

      <ManagementSummary kpis={kpis} />
    </main>
  );
}

