"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import {
  type AdvisorMetricsDto,
  fetchAdvisorMetrics,
} from "@/lib/api";
import {
  CH_BTN_PRIMARY,
  CH_CARD,
  CH_SECTION_LABEL,
  CH_SHELL,
} from "@/lib/boardLayout";
import { featureAdvisorMetricsInternal } from "@/lib/config";

function pct(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${(value * 100).toFixed(1)} %`;
}

function BarSegment({ color, ratio, label }: { color: string; ratio: number; label: string }) {
  if (ratio <= 0) return null;
  return (
    <div
      className={`flex items-center justify-center text-xs font-semibold text-white ${color}`}
      style={{ width: `${Math.max(ratio * 100, 8)}%`, minWidth: "2rem" }}
      title={label}
    >
      {label}
    </div>
  );
}

function DistributionBar({ data, total }: { data: Record<string, number>; total: number }) {
  if (total === 0) {
    return <p className="text-xs text-slate-500">Keine Daten</p>;
  }
  const colors: Record<string, string> = {
    high: "bg-emerald-500",
    medium: "bg-amber-500",
    low: "bg-red-500",
    bm25: "bg-cyan-600",
    hybrid: "bg-violet-600",
    answered: "bg-emerald-600",
    escalated: "bg-rose-500",
  };
  return (
    <div className="flex h-7 w-full overflow-hidden rounded-lg">
      {Object.entries(data).map(([key, count]) => (
        <BarSegment
          key={key}
          color={colors[key] ?? "bg-slate-400"}
          ratio={count / total}
          label={`${key}: ${count}`}
        />
      ))}
    </div>
  );
}

export default function AdvisorMetricsPage() {
  const enabled = featureAdvisorMetricsInternal();
  const [data, setData] = useState<AdvisorMetricsDto | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tenantFilter, setTenantFilter] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {};
      if (tenantFilter.trim()) params.tenant_id = tenantFilter.trim();
      const d = await fetchAdvisorMetrics(params);
      setData(d);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Metriken konnten nicht geladen werden.");
    } finally {
      setLoading(false);
    }
  }, [tenantFilter]);

  useEffect(() => {
    if (enabled) void load();
  }, [enabled, load]);

  const modeTotal = useMemo(
    () => Object.values(data?.retrieval_mode_distribution ?? {}).reduce((a, b) => a + b, 0),
    [data],
  );
  const confTotal = useMemo(
    () => Object.values(data?.confidence_distribution ?? {}).reduce((a, b) => a + b, 0),
    [data],
  );
  const decTotal = useMemo(
    () => Object.values(data?.agent_decision_distribution ?? {}).reduce((a, b) => a + b, 0),
    [data],
  );

  if (!enabled) {
    return (
      <div className={CH_SHELL}>
        <EnterprisePageHeader
          eyebrow="Internal"
          title="Advisor-Metriken"
          description="Feature deaktiviert (NEXT_PUBLIC_FEATURE_ADVISOR_METRICS_INTERNAL)."
        />
      </div>
    );
  }

  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        eyebrow="Internal / Engineering"
        title="Advisor-Metriken"
        description="Aggregierte Nutzungs-, Konfidenz- und Eskalationsdaten des Advisor-Stacks. Keine PII, nur Zähler und Kategorien."
      />

      <section className={`${CH_CARD} space-y-4`} aria-label="Filter">
        <p className={CH_SECTION_LABEL}>Filter</p>
        <div className="flex flex-wrap items-end gap-4">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-slate-600">Mandant (optional)</span>
            <input
              type="text"
              value={tenantFilter}
              onChange={(e) => setTenantFilter(e.target.value)}
              placeholder="z. B. tenant-001"
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
            />
          </label>
          <button type="button" className={CH_BTN_PRIMARY} onClick={() => void load()}>
            Aktualisieren
          </button>
        </div>
      </section>

      {loading ? (
        <p className="text-sm text-slate-600" role="status">Metriken werden geladen …</p>
      ) : error ? (
        <p className="text-sm text-red-800" role="alert">{error}</p>
      ) : data ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Anfragen gesamt" value={String(data.total_queries)} />
            <StatCard label="Eskalationsrate" value={pct(data.escalation_rate)} />
            <StatCard
              label="Hybrid-Anteil"
              value={pct(modeTotal > 0 ? (data.retrieval_mode_distribution.hybrid ?? 0) / modeTotal : null)}
            />
            <StatCard
              label="Hohe Konfidenz"
              value={pct(confTotal > 0 ? (data.confidence_distribution.high ?? 0) / confTotal : null)}
            />
          </div>

          <section className={`${CH_CARD} space-y-5`}>
            <div>
              <p className={CH_SECTION_LABEL}>Retrieval-Modus</p>
              <div className="mt-2">
                <DistributionBar data={data.retrieval_mode_distribution} total={modeTotal} />
              </div>
            </div>
            <div>
              <p className={CH_SECTION_LABEL}>Konfidenzverteilung</p>
              <div className="mt-2">
                <DistributionBar data={data.confidence_distribution} total={confTotal} />
              </div>
            </div>
            <div>
              <p className={CH_SECTION_LABEL}>Agent-Entscheidungen</p>
              <div className="mt-2">
                <DistributionBar data={data.agent_decision_distribution} total={decTotal} />
              </div>
            </div>
          </section>

          {data.daily.length > 0 ? (
            <section className={`${CH_CARD} overflow-x-auto p-0`}>
              <div className="border-b border-slate-200/80 px-5 py-4">
                <h2 className="text-sm font-semibold text-slate-900">Tagesübersicht</h2>
              </div>
              <table className="min-w-full border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/90 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    <th className="px-4 py-3">Datum</th>
                    <th className="px-4 py-3">Mandant</th>
                    <th className="px-4 py-3 text-right">Anfragen</th>
                    <th className="px-4 py-3 text-right">BM25</th>
                    <th className="px-4 py-3 text-right">Hybrid</th>
                    <th className="px-4 py-3 text-right">High</th>
                    <th className="px-4 py-3 text-right">Medium</th>
                    <th className="px-4 py-3 text-right">Low</th>
                    <th className="px-4 py-3 text-right">Beantwortet</th>
                    <th className="px-4 py-3 text-right">Eskaliert</th>
                  </tr>
                </thead>
                <tbody>
                  {data.daily.map((d, i) => (
                    <tr key={`${d.date}-${d.tenant_id}-${i}`} className="border-b border-slate-100">
                      <td className="px-4 py-2.5 text-slate-700">{d.date}</td>
                      <td className="px-4 py-2.5 font-mono text-xs text-slate-600">{d.tenant_id}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums">{d.total_queries}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums">{d.retrieval_mode_bm25}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums">{d.retrieval_mode_hybrid}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums">{d.confidence_high}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums">{d.confidence_medium}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums">{d.confidence_low}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums">{d.agent_answered}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums text-rose-700">{d.agent_escalated}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          ) : null}
        </>
      ) : null}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className={CH_CARD}>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">{value}</p>
    </div>
  );
}
