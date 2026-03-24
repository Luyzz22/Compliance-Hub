import React from "react";
import Link from "next/link";

import {
  fetchNis2KritisKpiDrilldown,
  type Nis2KritisKpiDrilldown,
  type Nis2KritisKpiType,
} from "@/lib/api";
import { BOARD_PAGE_MAIN_CLASS } from "@/lib/boardLayout";

const KPI_LABEL: Record<Nis2KritisKpiType, string> = {
  INCIDENT_RESPONSE_MATURITY: "Incident-Response-Reife",
  SUPPLIER_RISK_COVERAGE: "Supplier-Risk-Coverage",
  OT_IT_SEGREGATION: "OT/IT-Segmentierung",
};

function Histogram({
  buckets,
  maxCount,
}: {
  buckets: Nis2KritisKpiDrilldown["by_kpi_type"][0]["histogram"];
  maxCount: number;
}) {
  return (
    <div className="mt-3 space-y-2">
      {buckets.map((b) => {
        const w = maxCount > 0 ? Math.round((b.count / maxCount) * 100) : 0;
        return (
          <div key={`${b.range_min_inclusive}-${b.range_max_exclusive}`}>
            <div className="flex justify-between text-xs text-slate-600">
              <span>
                {b.range_min_inclusive}–{b.range_max_exclusive === 101 ? 100 : b.range_max_exclusive - 1}{" "}
                %
              </span>
              <span>{b.count}</span>
            </div>
            <div className="mt-0.5 h-2 w-full rounded bg-slate-100">
              <div
                className="h-2 rounded bg-slate-700"
                style={{ width: `${w}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default async function BoardNis2KritisPage() {
  let drilldown: Nis2KritisKpiDrilldown | null = null;
  try {
    drilldown = await fetchNis2KritisKpiDrilldown(5);
  } catch (error) {
    console.error("NIS2 drilldown API error:", error);
  }

  if (!drilldown) {
    return (
      <main className={BOARD_PAGE_MAIN_CLASS}>
        <header className="mb-6">
          <h1 className="sbs-h1">
            NIS2 / KRITIS – KPI-Drilldown
          </h1>
          <p className="sbs-subtitle">
            Incident-, Supplier- und OT/IT-KPIs je KI-System
          </p>
        </header>
        <div
          role="status"
          className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800"
        >
          Drilldown-Daten konnten nicht geladen werden.
        </div>
        <p className="mt-4">
          <Link
            href="/board/kpis"
            className="text-sm font-medium text-slate-600 underline hover:text-slate-900"
          >
            ← Zurück zu Board-KPIs
          </Link>
        </p>
      </main>
    );
  }

  return (
    <main className={BOARD_PAGE_MAIN_CLASS}>
      <header className="mb-6">
        <h1 className="sbs-h1">
          NIS2 / KRITIS – KPI-Drilldown
        </h1>
        <p className="sbs-subtitle">
          Verteilung der KPI-Prozentwerte und schwächste KI-Systeme je Typ
          (Top {drilldown.top_n}). Stand:{" "}
          {new Date(drilldown.generated_at).toLocaleString("de-DE")}
        </p>
        <p className="mt-2">
          <Link
            href="/board/kpis"
            className="text-sm font-medium text-slate-600 underline hover:text-slate-900"
          >
            ← Zurück zu Board-KPIs
          </Link>
        </p>
      </header>

      <div className="min-w-0 space-y-8">
        {drilldown.by_kpi_type.map((block) => {
          const maxCount = Math.max(
            ...block.histogram.map((h) => h.count),
            1,
          );
          return (
            <section
              key={block.kpi_type}
              aria-label={KPI_LABEL[block.kpi_type]}
              className="sbs-panel min-w-0 p-5"
            >
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                {KPI_LABEL[block.kpi_type]}
              </h2>
              <p className="mt-1 text-xs text-slate-500">
                Histogramm (Buckets 0–25, 25–50, 50–75, 75–100 %)
              </p>
              <Histogram buckets={block.histogram} maxCount={maxCount} />

              <h3 className="mt-6 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Top {drilldown.top_n} niedrigste Werte
              </h3>
              {block.critical_systems.length === 0 ? (
                <p className="mt-2 text-sm text-slate-500">
                  Keine KPI-Werte für diesen Typ erfasst.
                </p>
              ) : (
                <ul className="mt-2 divide-y divide-slate-100">
                  {block.critical_systems.map((s) => (
                    <li
                      key={`${s.ai_system_id}-${block.kpi_type}`}
                      className="flex min-w-0 flex-wrap items-baseline justify-between gap-2 py-2 text-sm"
                    >
                      <div className="min-w-0">
                        <span className="font-medium text-slate-900">
                          {s.name}
                        </span>
                        <span className="ml-2 text-slate-500">
                          {s.business_unit}
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="tabular-nums text-slate-700">
                          {s.value_percent} %
                        </span>
                        <Link
                          href={s.detail_href}
                          className="text-xs font-medium text-slate-600 underline hover:text-slate-900"
                        >
                          EU-AI-Act-Ansicht
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
    </main>
  );
}
