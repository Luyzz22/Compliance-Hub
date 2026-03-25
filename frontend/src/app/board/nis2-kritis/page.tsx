import React from "react";
import Link from "next/link";

import {
  fetchBoardKpis,
  fetchNis2KritisKpiDrilldown,
  type Nis2KritisKpiDrilldown,
  type Nis2KritisKpiType,
  type Nis2KritisKpiTypeDrilldown,
} from "@/lib/api";
import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import {
  BOARD_PAGE_ROOT_CLASS,
  CH_CARD,
  CH_PAGE_NAV_LINK,
  CH_SECTION_LABEL,
} from "@/lib/boardLayout";

const KPI_LABEL: Record<Nis2KritisKpiType, string> = {
  INCIDENT_RESPONSE_MATURITY: "Incident-Readiness",
  SUPPLIER_RISK_COVERAGE: "Supplier-Risk-Coverage",
  OT_IT_SEGREGATION: "OT/IT-Segmentierung",
};

function histogramApproxMean(block: Nis2KritisKpiTypeDrilldown): number | null {
  const buckets = block.histogram;
  let sum = 0;
  let n = 0;
  for (const b of buckets) {
    const hi = b.range_max_exclusive === 101 ? 100 : b.range_max_exclusive - 1;
    const mid = (b.range_min_inclusive + hi) / 2;
    sum += mid * b.count;
    n += b.count;
  }
  if (!n) return null;
  return Math.round(sum / n);
}

function VerticalBucketChart({
  buckets,
  maxCount,
}: {
  buckets: Nis2KritisKpiDrilldown["by_kpi_type"][0]["histogram"];
  maxCount: number;
}) {
  return (
    <div className="mt-6">
      <p className="text-xs text-slate-500">
        Legende: Balkenhöhe = Anteil am Maximum je Bucket (Anzahl Systeme).
      </p>
      <div className="mt-4 flex h-44 items-end justify-between gap-2 sm:h-48 sm:gap-3">
        {buckets.map((b) => {
          const h = maxCount > 0 ? Math.round((b.count / maxCount) * 100) : 0;
          const hi = b.range_max_exclusive === 101 ? 100 : b.range_max_exclusive - 1;
          return (
            <div
              key={`${b.range_min_inclusive}-${b.range_max_exclusive}`}
              className="flex min-w-0 flex-1 flex-col items-center gap-2"
            >
              <div className="flex h-36 w-full items-end justify-center rounded-t-xl bg-slate-100/90 sm:h-40">
                <div
                  className="w-[72%] min-h-[3px] rounded-t-lg bg-gradient-to-t from-cyan-700 to-teal-400 shadow-sm transition-all"
                  style={{ height: `${h}%` }}
                  title={`${b.count} Systeme`}
                />
              </div>
              <span className="text-center text-[0.65rem] font-semibold leading-tight text-slate-600">
                {b.range_min_inclusive}–{hi}%
              </span>
              <span className="tabular-nums text-xs font-bold text-slate-800">{b.count}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default async function BoardNis2KritisPage() {
  let drilldown: Nis2KritisKpiDrilldown | null = null;
  let boardKpis: Awaited<ReturnType<typeof fetchBoardKpis>> | null = null;

  const [ddRes, kpRes] = await Promise.allSettled([
    fetchNis2KritisKpiDrilldown(5),
    fetchBoardKpis(),
  ]);
  if (ddRes.status === "fulfilled") drilldown = ddRes.value;
  else console.error("NIS2 drilldown API error:", ddRes.reason);
  if (kpRes.status === "fulfilled") boardKpis = kpRes.value;
  else console.error("Board KPIs API error:", kpRes.reason);

  if (!drilldown) {
    return (
      <div className={BOARD_PAGE_ROOT_CLASS}>
        <EnterprisePageHeader
          eyebrow="Board"
          title="NIS2 / KRITIS"
          description="Incident- und Supplier-Readiness – Drilldown je KI-System."
          below={
            <Link href="/board/kpis" className={CH_PAGE_NAV_LINK}>
              Zurück zu Board KPIs
            </Link>
          }
        />
        <div
          role="status"
          className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
        >
          Drilldown-Daten konnten nicht geladen werden.
        </div>
      </div>
    );
  }

  const incidentBlock = drilldown.by_kpi_type.find(
    (b) => b.kpi_type === "INCIDENT_RESPONSE_MATURITY",
  );
  const supplierBlock = drilldown.by_kpi_type.find(
    (b) => b.kpi_type === "SUPPLIER_RISK_COVERAGE",
  );
  const otBlock = drilldown.by_kpi_type.find(
    (b) => b.kpi_type === "OT_IT_SEGREGATION",
  );

  const incidentMean = incidentBlock ? histogramApproxMean(incidentBlock) : null;
  const supplierMean = supplierBlock ? histogramApproxMean(supplierBlock) : null;
  const otMean = otBlock ? histogramApproxMean(otBlock) : null;

  const incidentPct =
    boardKpis != null
      ? Math.round(boardKpis.nis2_incident_readiness_ratio * 100)
      : incidentMean;
  const supplierPct =
    boardKpis != null
      ? Math.round(boardKpis.nis2_supplier_risk_coverage_ratio * 100)
      : supplierMean;
  const fullCoveragePct =
    boardKpis?.nis2_kritis_systems_full_coverage_ratio != null
      ? Math.round(boardKpis.nis2_kritis_systems_full_coverage_ratio * 100)
      : null;

  return (
    <div className={BOARD_PAGE_ROOT_CLASS}>
      <EnterprisePageHeader
        eyebrow="Board"
        title="NIS2 / KRITIS"
        description={`Incident- und Supplier-Readiness – Verteilung und schwächste Systeme (Top ${drilldown.top_n}). Stand: ${new Date(drilldown.generated_at).toLocaleString("de-DE")}.`}
        below={
          <>
            <Link href="/board/kpis" className={CH_PAGE_NAV_LINK}>
              Board KPIs
            </Link>
            <Link href="/board/incidents" className={CH_PAGE_NAV_LINK}>
              Incidents
            </Link>
            <Link href="/board/suppliers" className={CH_PAGE_NAV_LINK}>
              Supplier-Risiko
            </Link>
          </>
        }
      />

      <section
        aria-label="NIS2-KPI-Übersicht"
        className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
      >
        <div className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Incident-Readiness</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-slate-900">
            {incidentPct != null ? `${incidentPct} %` : "–"}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {boardKpis != null ? "Board-KPI (Runbooks)" : "Ø aus Histogramm"}
          </p>
        </div>
        <div className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Supplier-Risk-Coverage</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-slate-900">
            {supplierPct != null ? `${supplierPct} %` : "–"}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {boardKpis != null ? "Board-KPI (Register)" : "Ø aus Histogramm"}
          </p>
        </div>
        <div className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>OT/IT (Ø aus Verteilung)</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-slate-900">
            {otMean != null ? `${otMean} %` : "–"}
          </p>
          <p className="mt-1 text-xs text-slate-500">Histogramm-Mittel</p>
        </div>
        <div className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Volle NIS2-KPI-Abdeckung</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-slate-900">
            {fullCoveragePct != null ? `${fullCoveragePct} %` : "–"}
          </p>
          <p className="mt-1 text-xs text-slate-500">Alle drei KPI-Typen befüllt</p>
        </div>
      </section>

      <div className="min-w-0 space-y-8">
        {drilldown.by_kpi_type.map((block) => {
          const maxCount = Math.max(...block.histogram.map((h) => h.count), 1);
          return (
            <section
              key={block.kpi_type}
              aria-label={KPI_LABEL[block.kpi_type]}
              className={CH_CARD}
            >
              <h2 className="flex items-center gap-2 text-base font-semibold text-slate-900">
                <span aria-hidden>🛡️</span>
                {KPI_LABEL[block.kpi_type]}
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Verteilung über vier Bereiche (0–25 … 75–100&nbsp;%).
              </p>
              <VerticalBucketChart buckets={block.histogram} maxCount={maxCount} />

              <h3 className={`${CH_SECTION_LABEL} mt-8`}>
                Top {drilldown.top_n} Risiko-Systeme
              </h3>
              {block.critical_systems.length === 0 ? (
                <p className="mt-2 text-sm text-slate-500">
                  Keine KPI-Werte für diesen Typ erfasst.
                </p>
              ) : (
                <ul className="mt-3 divide-y divide-slate-100">
                  {block.critical_systems.map((s) => (
                    <li
                      key={`${s.ai_system_id}-${block.kpi_type}`}
                      className="flex min-w-0 flex-wrap items-center justify-between gap-3 py-4 text-sm transition first:pt-0 hover:bg-slate-50/90"
                    >
                      <div className="min-w-0">
                        <div className="font-semibold text-slate-900">{s.name}</div>
                        <div className="text-xs text-slate-500">{s.business_unit}</div>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="tabular-nums text-lg font-semibold text-slate-800">
                          {s.value_percent} %
                        </span>
                        <Link
                          href={`/tenant/ai-systems/${encodeURIComponent(s.ai_system_id)}`}
                          className="shrink-0 rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-slate-800"
                        >
                          System-Detail
                        </Link>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          );
        })}
      </div>
    </div>
  );
}
