"use client";

import { useEffect, useMemo, useState } from "react";

import { AdvisorBoardReportsPanel } from "@/components/advisor/AdvisorBoardReportsPanel";
import { AdvisorPortfolioExportToolbar, AdvisorPortfolioTable } from "@/components/advisor/AdvisorPortfolioTable";
import { DemoTenantSetupPanel } from "@/components/demo/DemoTenantSetupPanel";
import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import { AdvisorTenantUsagePicker } from "@/components/usage/TenantUsageSummary";
import {
  ADVISOR_ID_FROM_ENV,
  fetchAdvisorPortfolio,
  type AdvisorPortfolioTenantEntry,
} from "@/lib/api";
import { portfolioHealth } from "@/lib/advisorPortfolioHealth";
import {
  advisorPrioritySortKey,
  applyAdvisorPortfolioFilters,
  type PortfolioPillarFilter,
  type PortfolioScenarioFilter,
  type PortfolioSegmentFilter,
} from "@/lib/advisorPortfolioPriority";
import { CH_CARD, CH_SECTION_LABEL, CH_SHELL } from "@/lib/boardLayout";
import { PORTFOLIO_GOVERNANCE_MATURITY_NOTE } from "@/lib/governanceMaturityDeCopy";
import {
  featureAdvisorWorkspace,
  featureAiComplianceBoardReport,
  featureDemoSeeding,
} from "@/lib/config";

type SortKey =
  | "advisor_priority"
  | "readiness"
  | "nis2_mean"
  | "setup"
  | "high_risk";
type AdvisorTab = "portfolio" | "board_reports";

function nis2Mean(t: AdvisorPortfolioTenantEntry): number {
  return t.nis2_kritis_kpi_mean_percent ?? -1;
}

export default function AdvisorPortfolioPage() {
  const advisorId = ADVISOR_ID_FROM_ENV;
  const [rows, setRows] = useState<AdvisorPortfolioTenantEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("advisor_priority");
  const [sortAsc, setSortAsc] = useState(true);
  const [onlyCriticalFilter, setOnlyCriticalFilter] = useState(false);
  const [pillarFilter, setPillarFilter] = useState<PortfolioPillarFilter | null>(null);
  const [scenarioFilter, setScenarioFilter] = useState<PortfolioScenarioFilter | null>(null);
  const [segmentFilter, setSegmentFilter] = useState<PortfolioSegmentFilter | null>(null);
  const [onlyHighPriority, setOnlyHighPriority] = useState(false);
  const [loadAttempt, setLoadAttempt] = useState(0);
  const showBoardReportsTab =
    Boolean(advisorId) && featureAdvisorWorkspace() && featureAiComplianceBoardReport();
  const [advisorTab, setAdvisorTab] = useState<AdvisorTab>("portfolio");

  useEffect(() => {
    if (!advisorId) {
      setLoading(false);
      setError("Kein Berater konfiguriert (NEXT_PUBLIC_ADVISOR_ID).");
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchAdvisorPortfolio(advisorId);
        if (!cancelled) setRows(data.tenants);
      } catch (e) {
        if (!cancelled) {
          const hint =
            e instanceof Error && e.message
              ? ` (${e.message})`
              : "";
          setError(
            `Das Mandanten-Portfolio konnte nicht geladen werden.${hint} Bitte Netzwerk, API-Key und Header x-advisor-id prüfen und erneut versuchen.`,
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [advisorId, loadAttempt]);

  const processed = useMemo(() => {
    let list = applyAdvisorPortfolioFilters(rows, {
      pillar: pillarFilter,
      scenario: scenarioFilter,
      segment: segmentFilter,
      priorityBucket: onlyHighPriority ? "high" : null,
    });
    if (onlyCriticalFilter) {
      list = list.filter((t) => {
        const h = portfolioHealth(t.eu_ai_act_readiness, t.setup_progress_ratio);
        return h === "critical" || t.eu_ai_act_readiness < 0.6 || t.setup_progress_ratio < 0.5;
      });
    }
    const dir = sortAsc ? 1 : -1;
    list.sort((a, b) => {
      let va = 0;
      let vb = 0;
      if (sortKey === "advisor_priority") {
        va = advisorPrioritySortKey(a);
        vb = advisorPrioritySortKey(b);
      } else if (sortKey === "readiness") {
        va = a.eu_ai_act_readiness;
        vb = b.eu_ai_act_readiness;
      } else if (sortKey === "nis2_mean") {
        va = nis2Mean(a);
        vb = nis2Mean(b);
      } else if (sortKey === "setup") {
        va = a.setup_progress_ratio;
        vb = b.setup_progress_ratio;
      } else {
        va = a.high_risk_systems_count;
        vb = b.high_risk_systems_count;
      }
      if (va === vb) return a.tenant_name.localeCompare(b.tenant_name, "de");
      return va < vb ? -dir : dir;
    });
    return list;
  }, [
    rows,
    onlyCriticalFilter,
    sortKey,
    sortAsc,
    pillarFilter,
    scenarioFilter,
    segmentFilter,
    onlyHighPriority,
  ]);

  function togglePillar(p: PortfolioPillarFilter) {
    setPillarFilter((cur) => (cur === p ? null : p));
  }

  function toggleSegment(s: PortfolioSegmentFilter) {
    setSegmentFilter((cur) => (cur === s ? null : s));
  }

  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        eyebrow="Berater"
        title={advisorTab === "board_reports" ? "Mandanten-Reports" : "Mandanten-Portfolio"}
        description={
          advisorTab === "board_reports"
            ? "Gespeicherte AI-Compliance-Board-Reports der verknüpften Mandanten."
            : "Vergleich Kern-KPIs und Guided-Setup-Fortschritt über alle zugeordneten Mandanten. Tenant-Öffnen setzt den Workspace-Mandanten per Cookie und springt zur Compliance-Übersicht."
        }
        actions={
          advisorId && advisorTab === "portfolio" ? (
            <AdvisorPortfolioExportToolbar advisorId={advisorId} disabled={loading || !!error} />
          ) : null
        }
      />

      {showBoardReportsTab ? (
        <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-2" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={advisorTab === "portfolio"}
            className={`rounded-lg px-3 py-2 text-sm font-semibold ${
              advisorTab === "portfolio"
                ? "bg-slate-900 text-white"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
            onClick={() => setAdvisorTab("portfolio")}
          >
            Mandanten-Portfolio
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={advisorTab === "board_reports"}
            className={`rounded-lg px-3 py-2 text-sm font-semibold ${
              advisorTab === "board_reports"
                ? "bg-slate-900 text-white"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
            onClick={() => setAdvisorTab("board_reports")}
          >
            Mandanten-Reports
          </button>
        </div>
      ) : null}

      {!advisorId ? (
        <div className={CH_CARD}>
          <p className="text-sm text-slate-700">
            Bitte <code className="rounded bg-slate-100 px-1">NEXT_PUBLIC_ADVISOR_ID</code> setzen
            (z. B. E-Mail des Beraters) und denselben Wert in der API-Allowlist{" "}
            <code className="rounded bg-slate-100 px-1">COMPLIANCEHUB_ADVISOR_IDS</code>. Optional:{" "}
            <code className="rounded bg-slate-100 px-1">NEXT_PUBLIC_SHOW_ADVISOR_NAV=1</code> für
            die Navigation.
          </p>
        </div>
      ) : null}

      {error ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900">
          <p>{error}</p>
          {advisorId ? (
            <button
              type="button"
              className="mt-3 rounded-lg border border-rose-300 bg-white px-3 py-1.5 text-xs font-semibold text-rose-900 hover:bg-rose-100"
              onClick={() => setLoadAttempt((n) => n + 1)}
            >
              Erneut laden
            </button>
          ) : null}
        </div>
      ) : null}

      {advisorTab === "portfolio" ? (
        <>
          <section className={CH_CARD} aria-label="Filter und Sortierung">
            <p className={CH_SECTION_LABEL}>Ansicht</p>
            <p className="mt-1 max-w-3xl text-xs text-slate-600">
              Standard: Sortierung nach Beraterpriorität (hoch zuerst). Filter kombinieren sich per
              UND; Schnellfilter betonen Aufbau/Monitoring bzw. Optimierung laut Reife-Szenario.
            </p>
            <div className="mt-3 flex flex-wrap gap-2" role="group" aria-label="Schnellfilter">
              <button
                type="button"
                className={`rounded-lg border px-3 py-1.5 text-xs font-semibold ${
                  segmentFilter === "aufbau_monitoring"
                    ? "border-rose-300 bg-rose-50 text-rose-900"
                    : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                }`}
                onClick={() => toggleSegment("aufbau_monitoring")}
              >
                Aufbau / Monitoring nötig
              </button>
              <button
                type="button"
                className={`rounded-lg border px-3 py-1.5 text-xs font-semibold ${
                  segmentFilter === "optimierung"
                    ? "border-slate-400 bg-slate-100 text-slate-900"
                    : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                }`}
                onClick={() => toggleSegment("optimierung")}
              >
                Optimierung
              </button>
            </div>
            <div className="mt-2 flex flex-wrap gap-2" role="group" aria-label="Säulen-Fokus">
              <span className="self-center text-xs font-semibold text-slate-500">Fokus:</span>
              {(["readiness", "gai", "monitoring"] as const).map((p) => (
                <button
                  key={p}
                  type="button"
                  className={`rounded-lg border px-2.5 py-1 text-xs font-medium ${
                    pillarFilter === p
                      ? "border-cyan-400 bg-cyan-50 text-cyan-950"
                      : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                  }`}
                  onClick={() => togglePillar(p)}
                >
                  {p === "readiness" ? "Readiness" : p === "gai" ? "Governance-Aktivität" : "Monitoring"}
                </button>
              ))}
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-3">
              <label className="flex items-center gap-2 text-xs text-slate-600" htmlFor="adv-scenario">
                Reife-Szenario
              </label>
              <select
                id="adv-scenario"
                className="rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs"
                value={scenarioFilter ?? ""}
                onChange={(e) => {
                  const v = e.target.value;
                  setScenarioFilter(
                    v === "" ? null : (v as PortfolioScenarioFilter),
                  );
                }}
              >
                <option value="">Alle</option>
                <option value="a">A — Grundlagen</option>
                <option value="b">B — Monitoring nachziehen</option>
                <option value="c">C — Nutzung ausbauen</option>
                <option value="d">D — Feintuning</option>
              </select>
              <label className="flex items-center gap-2 text-xs text-slate-700">
                <input
                  type="checkbox"
                  checked={onlyHighPriority}
                  onChange={(e) => setOnlyHighPriority(e.target.checked)}
                />
                Nur hohe Priorität
              </label>
            </div>
            <div className="mt-4 flex flex-wrap items-end gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600" htmlFor="adv-sort">
                  Sortierung
                </label>
                <select
                  id="adv-sort"
                  className="mt-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
                  value={sortKey}
                  onChange={(e) => setSortKey(e.target.value as SortKey)}
                >
                  <option value="advisor_priority">Beraterpriorität</option>
                  <option value="readiness">EU AI Act Readiness</option>
                  <option value="nis2_mean">NIS2 KPI Mittelwert</option>
                  <option value="setup">Setup-Fortschritt</option>
                  <option value="high_risk">Anzahl High-Risk</option>
                </select>
              </div>
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={sortAsc}
                  onChange={(e) => setSortAsc(e.target.checked)}
                />
                Aufsteigend
              </label>
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={onlyCriticalFilter}
                  onChange={(e) => setOnlyCriticalFilter(e.target.checked)}
                />
                Nur kritische Mandanten (Readiness &lt; 0,6 oder Setup &lt; 50%)
              </label>
              {loading ? (
                <span className="text-xs text-slate-500">Lade Portfolio…</span>
              ) : (
                <span className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
                  {processed.length} Mandant(en)
                </span>
              )}
            </div>
          </section>

          {advisorId && featureDemoSeeding() ? (
            <DemoTenantSetupPanel advisorId={advisorId} defaultTenantId="" />
          ) : null}

          {advisorId ? (
            <AdvisorTenantUsagePicker
              advisorId={advisorId}
              tenantIds={[...new Set(processed.map((t) => t.tenant_id))]}
            />
          ) : null}

          <p className="mb-3 max-w-4xl text-xs leading-relaxed text-slate-600">
            {PORTFOLIO_GOVERNANCE_MATURITY_NOTE}
          </p>

          <AdvisorPortfolioTable rows={processed} advisorId={advisorId} />
        </>
      ) : advisorId ? (
        <AdvisorBoardReportsPanel advisorId={advisorId} />
      ) : null}
    </div>
  );
}
