"use client";

import Link from "next/link";

import {
  getAdvisorTenantReportUrl,
  type AdvisorGovernanceMaturityBriefDto,
  type AdvisorPortfolioTenantEntry,
} from "@/lib/api";
import { portfolioHealth, type PortfolioHealth } from "@/lib/advisorPortfolioHealth";
import { CH_BTN_PRIMARY, CH_BTN_SECONDARY, CH_CARD } from "@/lib/boardLayout";
import * as chConfig from "@/lib/config";
import {
  indexLevelLabelDe,
  PORTFOLIO_COL_EU_AI_ACT,
  PORTFOLIO_COL_EU_AI_ACT_TOOLTIP,
  PORTFOLIO_COL_GAI_SHORT,
  PORTFOLIO_COL_GAI_TOOLTIP,
  PORTFOLIO_COL_OAMI_SHORT,
  PORTFOLIO_COL_OAMI_TOOLTIP,
  PORTFOLIO_COL_READINESS,
  PORTFOLIO_COL_READINESS_TOOLTIP,
  readinessPortfolioBadgeTooltip,
} from "@/lib/governanceMaturityDeCopy";
import {
  priorityBadgeClasses,
  priorityLabelDe,
} from "@/lib/advisorPortfolioPriority";
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

function advisorBriefFocusMarker(brief: AdvisorGovernanceMaturityBriefDto): string {
  const a = brief.recommended_focus_areas?.[0]?.trim();
  if (a) {
    const t = a.length > 44 ? `${a.slice(0, 41)}…` : a;
    return `Fokus: ${t}`;
  }
  return `Gesamt: ${brief.governance_maturity_summary.overall_assessment.level}`;
}

function advisorBriefPortfolioTooltip(brief: AdvisorGovernanceMaturityBriefDto): string {
  const oa = brief.governance_maturity_summary.overall_assessment;
  const parts = [
    `Gesamtbild (konservativ): ${oa.level}.`,
    ...(brief.recommended_focus_areas ?? []).slice(0, 3),
    `Zeithorizont: ${brief.suggested_next_steps_window}`,
  ];
  return parts.join(" ").slice(0, 500);
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
  const governanceMaturityUi = chConfig.featureGovernanceMaturity();

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
              <th
                className="max-w-[6.5rem]"
                title="Regelbasiert aus Readiness, GAI, OAMI und Reife-Szenario A–D. Tooltip zeigt Begründung."
              >
                Priorität
              </th>
              <th
                className="max-w-[6rem]"
                title="Hauptschwerpunkt aus Kurzbrief oder Heuristik (Monitoring, Readiness, Nutzung, Governance)."
              >
                Schwerpunkt
              </th>
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
              {governanceMaturityUi ? (
                <>
                  <th title={PORTFOLIO_COL_GAI_TOOLTIP} className="max-w-[7rem]">
                    {PORTFOLIO_COL_GAI_SHORT}
                  </th>
                  <th title={PORTFOLIO_COL_OAMI_TOOLTIP} className="max-w-[7rem]">
                    {PORTFOLIO_COL_OAMI_SHORT}
                  </th>
                  <th
                    title="Strukturierter Berater-Kurzbrief (JSON-Felder; Tooltip mit Fokus und Horizont)"
                    className="max-w-[9rem]"
                  >
                    Reife-Brief
                  </th>
                </>
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
                    <div
                      className="mt-1 flex flex-wrap items-center gap-1"
                      data-testid={`advisor-regulatory-row-${t.tenant_id}`}
                    >
                      {t.nis2_entity_category === "essential_entity" ? (
                        <span
                          className="rounded bg-violet-50 px-1.5 py-0.5 text-[0.6rem] font-bold uppercase tracking-wide text-violet-900 ring-1 ring-violet-200"
                          title="NIS2: wesentliche Einrichtung"
                        >
                          NIS2 wesentl.
                        </span>
                      ) : t.nis2_entity_category === "important_entity" ? (
                        <span
                          className="rounded bg-slate-100 px-1.5 py-0.5 text-[0.6rem] font-semibold text-slate-800 ring-1 ring-slate-200"
                          title="NIS2: wichtige Einrichtung oder allgemeine NIS2-Relevanz (Stammdaten)"
                        >
                          NIS2
                        </span>
                      ) : null}
                      {t.kritis_sector_key ? (
                        <span
                          className="rounded bg-amber-50 px-1.5 py-0.5 text-[0.6rem] font-semibold text-amber-950 ring-1 ring-amber-200"
                          title={`KRITIS-Sektor: ${t.kritis_sector_key}`}
                          data-testid={`advisor-kritis-badge-${t.tenant_id}`}
                        >
                          KRITIS
                        </span>
                      ) : null}
                      {t.recent_incidents_90d ? (
                        <span
                          className="inline-flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-rose-50 px-1 text-[0.65rem] font-bold text-rose-800 ring-1 ring-rose-200"
                          title={`Vorfälle in den letzten 90 Tagen; Laststufe: ${t.incident_burden_level ?? "?"}. Keine Einzelfallinhalte.`}
                          aria-label="Hinweis: Vorfälle in den letzten 90 Tagen"
                          data-testid={`advisor-incident-flag-${t.tenant_id}`}
                        >
                          !
                        </span>
                      ) : null}
                    </div>
                  </td>
                  <td
                    className="align-middle text-xs"
                    data-testid={`advisor-priority-${t.tenant_id}`}
                  >
                    <span
                      className="inline-flex flex-col items-start gap-0.5"
                      title={
                        t.advisor_priority_explanation_de?.trim() ||
                        "Priorität basiert auf Readiness, Governance-Aktivität (GAI), operativem Monitoring (OAMI) und Reife-Szenario A–D (regelbasiert)."
                      }
                    >
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${priorityBadgeClasses(t.advisor_priority)}`}
                      >
                        {priorityLabelDe(t.advisor_priority)}
                      </span>
                      {t.maturity_scenario_hint ? (
                        <span className="text-[0.65rem] font-medium text-slate-600">
                          Sz. {t.maturity_scenario_hint.toUpperCase()}
                        </span>
                      ) : null}
                    </span>
                  </td>
                  <td
                    className="align-middle text-xs"
                    data-testid={`advisor-primary-focus-${t.tenant_id}`}
                  >
                    {t.primary_focus_tag_de ? (
                      <span
                        className="inline-flex max-w-[6.5rem] truncate rounded-full bg-cyan-50 px-2 py-0.5 font-medium text-cyan-900 ring-1 ring-cyan-200"
                        title={
                          (t.governance_maturity_advisor_brief?.recommended_focus_areas?.[0] ??
                            t.advisor_priority_explanation_de ??
                            "").trim() || undefined
                        }
                      >
                        {t.primary_focus_tag_de}
                      </span>
                    ) : (
                      <span className="text-[var(--sbs-text-muted)]">–</span>
                    )}
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
                          title={readinessPortfolioBadgeTooltip(t.readiness_summary.level)}
                          data-testid={`advisor-readiness-badge-${t.tenant_id}`}
                        >
                          {t.readiness_summary.score}
                        </span>
                      ) : (
                        <span className="text-xs text-[var(--sbs-text-muted)]">–</span>
                      )}
                    </td>
                  ) : null}
                  {governanceMaturityUi ? (
                    <>
                      <td
                        className="text-center align-middle text-xs tabular-nums text-[var(--sbs-text-secondary)]"
                        data-testid={`advisor-gai-cell-${t.tenant_id}`}
                      >
                        {t.governance_activity_summary ? (
                          <span title={PORTFOLIO_COL_GAI_TOOLTIP}>
                            {t.governance_activity_summary.index}
                            <span className="text-[var(--sbs-text-muted)]">
                              {" "}
                              · {indexLevelLabelDe(t.governance_activity_summary.level)}
                            </span>
                          </span>
                        ) : (
                          <span className="text-[var(--sbs-text-muted)]">–</span>
                        )}
                      </td>
                      <td
                        className="text-center align-middle text-xs tabular-nums text-[var(--sbs-text-secondary)]"
                        data-testid={`advisor-oami-cell-${t.tenant_id}`}
                      >
                        {t.operational_monitoring_summary?.level != null ? (
                          <span
                            title={[
                              PORTFOLIO_COL_OAMI_TOOLTIP,
                              t.operational_monitoring_summary.oami_operational_hint_de,
                              (t.operational_monitoring_summary.safety_related_runtime_incidents_90d ??
                                0) > 0
                                ? `Sicherheitsrelevante Laufzeit-Incidents (90 Tage): ${t.operational_monitoring_summary.safety_related_runtime_incidents_90d}`
                                : "",
                            ]
                              .filter(Boolean)
                              .join(" ")}
                          >
                            {t.operational_monitoring_summary.index ?? "–"}
                            <span className="text-[var(--sbs-text-muted)]">
                              {" "}
                              · {indexLevelLabelDe(t.operational_monitoring_summary.level)}
                            </span>
                            {(t.operational_monitoring_summary.safety_related_runtime_incidents_90d ??
                              0) > 0 ? (
                              <span className="mt-0.5 block text-[0.6rem] leading-tight text-rose-800">
                                Sicherheit:{" "}
                                {t.operational_monitoring_summary.safety_related_runtime_incidents_90d}
                              </span>
                            ) : null}
                          </span>
                        ) : (
                          <span className="text-[var(--sbs-text-muted)]">–</span>
                        )}
                      </td>
                      <td
                        className="align-middle text-xs text-[var(--sbs-text-secondary)]"
                        data-testid={`advisor-gm-brief-${t.tenant_id}`}
                      >
                        {t.governance_maturity_advisor_brief ? (
                          <span
                            className="block max-w-[11rem] truncate font-medium text-slate-800"
                            title={advisorBriefPortfolioTooltip(t.governance_maturity_advisor_brief)}
                          >
                            {advisorBriefFocusMarker(t.governance_maturity_advisor_brief)}
                          </span>
                        ) : (
                          <span className="text-[var(--sbs-text-muted)]">–</span>
                        )}
                      </td>
                    </>
                  ) : null}
                  {snapUi ? (
                    <td className="align-top">
                      <Link
                        href={`/advisor/clients/${encodeURIComponent(t.tenant_id)}/governance-snapshot?highlight=governance-maturity`}
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
