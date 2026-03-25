"use client";

import { getAdvisorTenantReportUrl, type AdvisorPortfolioTenantEntry } from "@/lib/api";
import { portfolioHealth, type PortfolioHealth } from "@/lib/advisorPortfolioHealth";
import { CH_BTN_PRIMARY, CH_BTN_SECONDARY, CH_CARD } from "@/lib/boardLayout";
import { featurePilotRunbook } from "@/lib/config";
import {
  openWorkspaceTenantAndGo,
  openWorkspaceTenantAndGoComplianceOverview,
} from "@/lib/workspaceTenantClient";

function badgeClasses(h: PortfolioHealth): string {
  if (h === "critical") {
    return "bg-rose-100 text-rose-900 ring-1 ring-rose-200";
  }
  if (h === "attention") {
    return "bg-amber-100 text-amber-950 ring-1 ring-amber-200";
  }
  return "bg-emerald-100 text-emerald-900 ring-1 ring-emerald-200";
}

function badgeLabel(h: PortfolioHealth): string {
  if (h === "critical") return "Critical";
  if (h === "attention") return "Attention";
  return "On Track";
}

export interface AdvisorPortfolioTableProps {
  rows: AdvisorPortfolioTenantEntry[];
  /** Für Steckbrief-Links (Proxy); leer = keine Download-CTAs. */
  advisorId: string;
}

export function AdvisorPortfolioTable({ rows, advisorId }: AdvisorPortfolioTableProps) {
  if (rows.length === 0) {
    return (
      <p className="rounded-xl border border-slate-200 bg-white px-4 py-8 text-center text-sm text-slate-600">
        Keine Mandanten in diesem Portfolio.
      </p>
    );
  }

  return (
    <div className={`${CH_CARD} overflow-hidden p-0`}>
      <div className="sbs-table-wrap">
        <table className="sbs-table">
          <thead>
            <tr>
              <th>Mandant</th>
              <th>Branche / Land</th>
              <th>EU AI Act Readiness</th>
              <th>NIS2 Ø / Coverage</th>
              <th>High-Risk</th>
              <th>Setup</th>
              <th>Offene Actions</th>
              <th>Status</th>
              <th>Mandanten-Steckbrief</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((t) => {
              const h = portfolioHealth(t.eu_ai_act_readiness, t.setup_progress_ratio);
              const nis2 =
                t.nis2_kritis_kpi_mean_percent != null
                  ? `${Math.round(t.nis2_kritis_kpi_mean_percent)}%`
                  : "–";
              const cov = `${Math.round(t.nis2_kritis_systems_full_coverage_ratio * 100)}%`;
              return (
                <tr key={t.tenant_id}>
                  <td>
                    <div className="font-semibold text-[var(--sbs-text-primary)]">
                      {t.tenant_name}
                    </div>
                    <div className="text-xs font-mono text-[var(--sbs-text-muted)]">
                      {t.tenant_id}
                    </div>
                  </td>
                  <td className="text-sm text-[var(--sbs-text-secondary)]">
                    {[t.industry, t.country].filter(Boolean).join(" · ") || "–"}
                  </td>
                  <td className="tabular-nums text-sm">
                    {Math.round(t.eu_ai_act_readiness * 100)}%
                  </td>
                  <td className="text-xs text-[var(--sbs-text-secondary)]">
                    {nis2}
                    <span className="mx-1 text-slate-300">|</span>
                    {cov}
                  </td>
                  <td className="tabular-nums text-sm">{t.high_risk_systems_count}</td>
                  <td className="text-sm tabular-nums">
                    {t.setup_completed_steps}/{t.setup_total_steps}
                  </td>
                  <td className="tabular-nums text-sm">{t.open_governance_actions_count}</td>
                  <td>
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${badgeClasses(h)}`}
                    >
                      {badgeLabel(h)}
                    </span>
                  </td>
                  <td className="text-right align-top">
                    {advisorId ? (
                      <div className="flex flex-col items-end gap-1">
                        <a
                          href={getAdvisorTenantReportUrl(t.tenant_id, "markdown", advisorId)}
                          className={`${CH_BTN_SECONDARY} inline-block text-xs no-underline`}
                          title="Mandanten-Steckbrief für Angebot, Board oder Kickoff (Markdown)"
                        >
                          Steckbrief (MD)
                        </a>
                        <a
                          href={getAdvisorTenantReportUrl(t.tenant_id, "json", advisorId)}
                          className="text-xs font-medium text-slate-600 underline decoration-slate-300 underline-offset-2 hover:text-slate-900"
                          title="Strukturierte Daten für Integrationen"
                        >
                          JSON
                        </a>
                      </div>
                    ) : (
                      <span className="text-xs text-slate-400">–</span>
                    )}
                  </td>
                  <td className="text-right">
                    <div className="flex flex-col items-end gap-1">
                      <button
                        type="button"
                        className={`${CH_BTN_PRIMARY} text-xs`}
                        onClick={() => openWorkspaceTenantAndGoComplianceOverview(t.tenant_id)}
                      >
                        Tenant öffnen
                      </button>
                      {featurePilotRunbook() ? (
                        <button
                          type="button"
                          className="text-xs font-medium text-cyan-800 underline decoration-cyan-300 underline-offset-2 hover:text-cyan-950"
                          onClick={() => openWorkspaceTenantAndGo(t.tenant_id, "/tenant/pilot-runbook")}
                        >
                          Pilot-Runbook (Kunde)
                        </button>
                      ) : null}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function AdvisorPortfolioExportToolbar({
  advisorId,
  disabled,
}: {
  advisorId: string;
  disabled?: boolean;
}) {
  async function download(format: "json" | "csv") {
    const { fetchAdvisorPortfolioExportBlob } = await import("@/lib/api");
    const blob = await fetchAdvisorPortfolioExportBlob(advisorId, format);
    const day = new Date().toISOString().slice(0, 10);
    const ext = format === "csv" ? "csv" : "json";
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `advisor-portfolio-${day}.${ext}`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  return (
    <div className="flex flex-wrap gap-2">
      <button
        type="button"
        disabled={disabled}
        className={`${CH_BTN_SECONDARY} text-xs disabled:opacity-50`}
        onClick={() => void download("json")}
      >
        Portfolio JSON
      </button>
      <button
        type="button"
        disabled={disabled}
        className={`${CH_BTN_SECONDARY} text-xs disabled:opacity-50`}
        onClick={() => void download("csv")}
      >
        Portfolio CSV
      </button>
    </div>
  );
}
