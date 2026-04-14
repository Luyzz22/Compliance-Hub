import React from "react";
import Link from "next/link";

import { fetchBoardKpiReport, type BoardKpiReport } from "@/lib/api";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";
import { PdfReportDownloadButton } from "./PdfReportDownloadButton";
import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import {
  BOARD_PAGE_ROOT_CLASS,
  CH_CARD,
  CH_CARD_MUTED,
  CH_PAGE_NAV_LINK,
  CH_SECTION_LABEL,
  chKpiStatusFromRatio,
} from "@/lib/boardLayout";

/* ── Heat-map severity colors ─────────────────────────────────────── */

function severityColor(score: number): string {
  if (score >= 75) return "bg-emerald-100 text-emerald-900";
  if (score >= 50) return "bg-amber-100 text-amber-950";
  return "bg-red-100 text-red-900";
}

function statusDot(score: number): string {
  if (score >= 75) return "bg-emerald-500";
  if (score >= 50) return "bg-amber-500";
  return "bg-red-500";
}

/* ── Page ──────────────────────────────────────────────────────────── */

export default async function ExecutiveDashboardPage() {
  const tenantId = await getWorkspaceTenantIdServer();
  let report: BoardKpiReport | null = null;

  try {
    report = await fetchBoardKpiReport(tenantId);
  } catch (error) {
    console.error("Executive Dashboard API error:", error);
  }

  if (!report) {
    return (
      <div className={BOARD_PAGE_ROOT_CLASS}>
        <EnterprisePageHeader
          eyebrow="Board"
          title="Executive Dashboard"
          description="Aggregierte Compliance-KPIs für Vorstand und Aufsichtsrat."
        />
        <div
          role="status"
          className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
        >
          Dashboard-Daten konnten nicht geladen werden. Bitte versuchen Sie es
          später erneut.
        </div>
      </div>
    );
  }

  const { compliance_score, incident_statistics, upcoming_deadlines } = report;
  const overallRatio = compliance_score.overall_score / 100;
  const overallStatus = chKpiStatusFromRatio(overallRatio);

  return (
    <div className={BOARD_PAGE_ROOT_CLASS}>
      <EnterprisePageHeader
        eyebrow="Board"
        title="Executive Dashboard"
        description="Aggregierte Compliance-KPIs für Vorstand und Aufsichtsrat — rollengesteuert."
        below={
          <>
            <Link href="/board/kpis" className={CH_PAGE_NAV_LINK}>
              Board KPIs
            </Link>
            <Link href="/board/gap-analysis" className={CH_PAGE_NAV_LINK}>
              Gap-Analyse
            </Link>
            <Link href="/board/datev-export" className={CH_PAGE_NAV_LINK}>
              DATEV Export
            </Link>
            <Link href="/board/xrechnung-export" className={CH_PAGE_NAV_LINK}>
              XRechnung Export
            </Link>
            <Link href="/board/n8n-workflows" className={CH_PAGE_NAV_LINK}>
              n8n Workflows
            </Link>
          </>
        }
      />

      {/* ── Overall Compliance Score ── */}
      <section aria-label="Compliance Score" className="mb-8">
        <p className={CH_SECTION_LABEL}>Overall Compliance Score</p>
        <div className={`${CH_CARD} mt-3 flex items-center gap-6`}>
          <div className="flex flex-col items-center">
            <span className="text-4xl font-bold tracking-tight text-slate-900">
              {compliance_score.overall_score}%
            </span>
            <span
              className={`mt-1 inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${overallStatus.chipClass}`}
            >
              {overallStatus.label}
            </span>
          </div>
          <div className="flex-1 text-sm text-slate-600">
            Gewichteter Index aller Normen. Stand:{" "}
            {compliance_score.computed_at?.slice(0, 10) ?? "–"}
          </div>
        </div>
      </section>

      {/* ── Heat Map: Norm × Score ── */}
      <section aria-label="Compliance Heat Map" className="mb-8">
        <p className={CH_SECTION_LABEL}>Risiko-Heat-Map (Norm × Score)</p>
        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {compliance_score.norm_scores.map((ns) => (
            <div
              key={ns.norm}
              className={`${CH_CARD} flex flex-col items-center gap-1`}
            >
              <div className={`inline-flex h-3 w-3 rounded-full ${statusDot(ns.score)}`} />
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                {ns.norm.replace(/_/g, " ")}
              </span>
              <span className={`rounded-lg px-3 py-1 text-lg font-bold ${severityColor(ns.score)}`}>
                {ns.score}%
              </span>
              <span className="text-[10px] text-slate-400">
                Gewicht: {(ns.weight * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* ── KPI Cards ── */}
      <section
        aria-label="KPI Summary"
        className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
      >
        <div className={CH_CARD}>
          <p className="text-xs font-semibold uppercase text-slate-500">
            High-Risk KI-Systeme
          </p>
          <p className="mt-1 text-2xl font-bold text-slate-900">
            {report.high_risk_ai_systems}
          </p>
        </div>
        <div className={CH_CARD}>
          <p className="text-xs font-semibold uppercase text-slate-500">
            Incidents (gesamt)
          </p>
          <p className="mt-1 text-2xl font-bold text-slate-900">
            {incident_statistics.total}
          </p>
        </div>
        <div className={CH_CARD}>
          <p className="text-xs font-semibold uppercase text-slate-500">
            Offen
          </p>
          <p className="mt-1 text-2xl font-bold text-red-700">
            {incident_statistics.open}
          </p>
        </div>
        <div className={CH_CARD}>
          <p className="text-xs font-semibold uppercase text-slate-500">
            Geschlossen
          </p>
          <p className="mt-1 text-2xl font-bold text-emerald-700">
            {incident_statistics.closed}
          </p>
        </div>
      </section>

      {/* ── Trend Data ── */}
      {report.trend_data.length > 0 && (
        <section aria-label="Trend" className="mb-8">
          <p className={CH_SECTION_LABEL}>Compliance-Reife (Quartals-Trend)</p>
          <div className={`${CH_CARD_MUTED} mt-3`}>
            <div className="flex gap-6 overflow-x-auto">
              {report.trend_data.map((t) => (
                <div key={t.period} className="flex flex-col items-center">
                  <span className="text-lg font-bold text-slate-900">
                    {t.score}%
                  </span>
                  <span className="text-xs text-slate-500">{t.period}</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ── Upcoming Deadlines ── */}
      <section aria-label="Deadlines" className="mb-8">
        <p className={CH_SECTION_LABEL}>Anstehende Fristen</p>
        <div className="mt-3 space-y-2">
          {upcoming_deadlines.map((d) => (
            <div
              key={d.deadline}
              className={`${CH_CARD} flex items-center gap-4`}
            >
              <span className="whitespace-nowrap rounded-lg bg-cyan-100 px-3 py-1 text-sm font-semibold text-cyan-900">
                {d.deadline}
              </span>
              <div>
                <p className="text-sm font-semibold text-slate-900">
                  {d.norm}
                </p>
                <p className="text-xs text-slate-500">{d.description}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Top Findings ── */}
      {report.top_findings.length > 0 && (
        <section aria-label="Top Findings" className="mb-8">
          <p className={CH_SECTION_LABEL}>
            Top-5 offene Findings
          </p>
          <div className="mt-3 space-y-2">
            {report.top_findings.map((f) => (
              <div key={f.id} className={CH_CARD}>
                <p className="text-sm font-semibold text-slate-900">
                  {f.event_type}
                </p>
                <p className="mt-0.5 text-xs text-slate-500">
                  {f.detail ?? "–"} · {f.created_at?.slice(0, 10) ?? "–"}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}
      {/* ── PDF/A-3 Board Report Download ── */}
      <section aria-label="PDF Report" className="mb-8">
        <p className={CH_SECTION_LABEL}>Board Report (PDF/A-3)</p>
        <div className={`${CH_CARD} mt-3`}>
          <p className="mb-3 text-sm text-slate-600">
            PDF/A-3 konformen Board-Report herunterladen – GoBD-archivierungssicher
            mit allen KPIs, Heat-Map, Findings und Signaturblock.
          </p>
          <PdfReportDownloadButton />
        </div>
      </section>
    </div>
  );
}
