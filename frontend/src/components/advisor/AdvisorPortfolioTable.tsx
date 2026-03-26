"use client";

import Link from "next/link";

import { getAdvisorTenantReportUrl, type AdvisorPortfolioTenantEntry } from "@/lib/api";
import { portfolioHealth, type PortfolioHealth } from "@/lib/advisorPortfolioHealth";
import { CH_BTN_PRIMARY, CH_BTN_SECONDARY, CH_CARD } from "@/lib/boardLayout";
import * as chConfig from "@/lib/config";
import {
  PORTFOLIO_COL_EU_AI_ACT,
  PORTFOLIO_COL_EU_AI_ACT_TOOLTIP,
  PORTFOLIO_COL_READINESS,
  PORTFOLIO_COL_READINESS_TOOLTIP,
  READINESS_REG_HINT_SHORT,
  readinessLevelLabelDe,
} from "@/lib/governanceMaturityDeCopy";
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

function crossRegCoverageIndicator(meanPercent: number | null | undefined): {
  label: string;
  dotClass: string;
} {
  if (meanPercent == null || Number.isNaN(meanPercent)) {
    return { label: "–", dotClass: "bg-slate-300" };
  }
  const p = Math.round(meanPercent);
  if (p >= 70) return { label: `${p}%`, dotClass: "bg-emerald-500" };
  if (p >= 40) return { label: `${p}%`, dotClass: "bg-amber-500" };
  return { label: `${p}%`, dotClass: "bg-rose-500" };
}

export interface AdvisorPortfolioTableProps {
  rows: AdvisorPortfolioTenantEntry[];
  /** Für Steckbrief-Links (Proxy); leer = keine Download-CTAs. */
  advisorId: string;
}

function readinessBadgeClasses(score: number): string {
  if (score < 40) return "bg-rose-100 text-rose-900 ring-1 ring-rose-200";
  if (score < 70) return "bg-amber-100 text-amber-950 ring-1 ring-amber-200";
  return "bg-emerald-100 text-emerald-900 ring-1 ring-emerald-200";
}

export function AdvisorPortfolioTable({ rows, advisorId }: AdvisorPortfolioTableProps) {
  const snapUi = chConfig.featureAdvisorClientSnapshot();
  const readinessUi = chConfig.featureReadinessScore();

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
              {snapUi ? (
                <>
                  <th>Frameworks</th>
                  <th>AI-Gov Wizard</th>
                  <th>Cross-Reg Ø</th>
                </>
              ) : null}
              <th title={PORTFOLIO_COL_EU_AI_ACT_TOOLTIP} className="max-w-[7rem]">
                {PORTFOLIO_COL_EU_AI_ACT}
              </th>
              <th>NIS2 Ø / Coverage</th>
              <th>High-Risk</th>
              <th>Setup</th>
              <th>Offene Actions</th>
              <th>Status</th>
              {readinessUi ? (
                <th title={PORTFOLIO_COL_READINESS_TOOLTIP} className="max-w-[6rem]">
                  {PORTFOLIO_COL_READINESS}
                </th>
              ) : null}
              {snapUi ? <th>Snapshot</th> : null}
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
              const brief = t.governance_brief;
              const covInd = crossRegCoverageIndicator(brief?.cross_reg_mean_coverage_percent);
              const fwKeys = brief?.active_framework_keys ?? [];
              const fwShow = fwKeys.slice(0, 3);
              const fwMore = fwKeys.length > 3 ? fwKeys.length - 3 : 0;
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
                  {snapUi ? (
                    <>
                      <td className="align-top text-xs">
                        {fwKeys.length ? (
                          <div className="flex max-w-[10rem] flex-wrap gap-1">
                            {fwShow.map((k) => (
                              <span
                                key={k}
                                className="rounded bg-cyan-50 px-1.5 py-0.5 font-semibold text-cyan-900"
                              >
                                {k}
                              </span>
                            ))}
                            {fwMore > 0 ? (
                              <span className="text-[var(--sbs-text-muted)]">+{fwMore}</span>
                            ) : null}
                          </div>
                        ) : (
                          <span className="text-[var(--sbs-text-muted)]">–</span>
                        )}
                      </td>
                      <td className="tabular-nums text-sm text-[var(--sbs-text-secondary)]">
                        {brief
                          ? `${brief.wizard_progress_count}/${brief.wizard_steps_total}`
                          : "–"}
                      </td>
                      <td className="text-sm">
                        <span className="inline-flex items-center gap-1.5 tabular-nums">
                          <span
                            className={`inline-block h-2 w-2 shrink-0 rounded-full ${covInd.dotClass}`}
                            title="Mittlere Framework-Coverage (Cross-Regulation)"
                            aria-hidden
                          />
                          {covInd.label}
                        </span>
                      </td>
                    </>
                  ) : null}
                  <td className="tabular-nums text-sm">
                    {Math.round(t.eu_ai_act_readiness * 100)}%
                  </td>
                  <td className="text-xs text-[var(--sbs-text-secondary)]">
                    {nis2}
                    <span className="mx-1 text-slate-300">|</span>
                    {cov}
                  </td>
                  <td className="text-sm tabular-nums">
                    <div>{t.high_risk_systems_count}</div>
                    {snapUi && brief != null ? (
                      <div className="text-xs font-normal text-[var(--sbs-text-muted)]">
                        NIS2-krit.: {brief.nis2_critical_ai_count}
                      </div>
                    ) : null}
                  </td>
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
                  {readinessUi ? (
                    <td className="text-center align-middle">
                      {t.readiness_summary ? (
                        <span
                          className={`inline-flex min-w-[2.25rem] justify-center rounded-full px-2 py-0.5 text-xs font-bold tabular-nums ${readinessBadgeClasses(t.readiness_summary.score)}`}
                          title={`Reifegrad ${readinessLevelLabelDe(t.readiness_summary.level)} (0–100). ${READINESS_REG_HINT_SHORT}`}
                          data-testid={`advisor-readiness-badge-${t.tenant_id}`}
                        >
                          {t.readiness_summary.score}
                        </span>
                      ) : (
                        <span className="text-xs text-[var(--sbs-text-muted)]">–</span>
                      )}
                    </td>
                  ) : null}
                  {snapUi ? (
                    <td className="align-top">
                      <Link
                        href={`/advisor/clients/${encodeURIComponent(t.tenant_id)}/governance-snapshot`}
                        className={`${CH_BTN_SECONDARY} inline-block text-xs no-underline`}
                        data-testid={`advisor-snapshot-link-${t.tenant_id}`}
                      >
                        Snapshot anzeigen
                      </Link>
                    </td>
                  ) : null}
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
                      {chConfig.featurePilotRunbook() ? (
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
