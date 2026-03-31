"use client";

import Link from "next/link";
import React, { useCallback, useEffect, useMemo, useState } from "react";

import { fetchTenantAiKpiSummary, type AiKpiSummaryResponseDto } from "@/lib/api";
import { CH_BTN_SECONDARY, CH_CARD, CH_SECTION_LABEL } from "@/lib/boardLayout";

function trendArrow(t: string): string {
  if (t === "up") return "↑";
  if (t === "down") return "↓";
  return "→";
}

export function AiKpiPortfolioStrip({
  tenantId,
  boardLayout = false,
}: {
  tenantId: string;
  /** Board-Seite: etwas kompaktere Typo */
  boardLayout?: boolean;
}) {
  const [data, setData] = useState<AiKpiSummaryResponseDto | null>(null);
  const [fw, setFw] = useState<string>("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(true);

  const load = useCallback(async () => {
    setBusy(true);
    setErr(null);
    try {
      const d = await fetchTenantAiKpiSummary(tenantId, {
        framework_key: fw || undefined,
      });
      setData(d);
    } catch (e) {
      setData(null);
      setErr(e instanceof Error ? e.message : "Laden fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  }, [tenantId, fw]);

  useEffect(() => {
    void load();
  }, [load]);

  const top = useMemo(() => {
    if (!data?.per_kpi?.length) return [];
    const withVals = data.per_kpi.filter((p) => p.avg_latest != null);
    const sorted = [...withVals].sort((a, b) => (b.avg_latest ?? 0) - (a.avg_latest ?? 0));
    return sorted.slice(0, 5);
  }, [data]);

  const labelCls = boardLayout ? "text-[11px]" : CH_SECTION_LABEL;

  return (
    <section
      className={CH_CARD}
      aria-label="AI-KPI-Portfolio High-Risk"
      data-testid="ai-kpi-portfolio-strip"
    >
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className={labelCls}>AI Performance &amp; Risk KPIs</p>
          <p
            className={
              boardLayout
                ? "mt-1 max-w-2xl text-xs text-slate-600"
                : "mt-1 max-w-2xl text-sm text-slate-600"
            }
          >
            Aggregierte Kennzahlen über High-Risk-/Unacceptable-KI-Systeme (Post-Market-Monitoring /
            Performance Evaluation). Filter optional nach Regelwerks-Tag.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select
            className="rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs"
            value={fw}
            onChange={(e) => setFw(e.target.value)}
            aria-label="Framework-Filter"
          >
            <option value="">Alle Framework-Tags</option>
            <option value="eu_ai_act">EU AI Act</option>
            <option value="iso_42001">ISO 42001</option>
            <option value="nis2">NIS2</option>
            <option value="dsgvo">DSGVO</option>
          </select>
          <button type="button" className={`${CH_BTN_SECONDARY} text-xs`} onClick={() => void load()}>
            Aktualisieren
          </button>
        </div>
      </div>

      {busy ? <p className="mt-3 text-sm text-slate-500">Lade KPI-Summary…</p> : null}
      {err ? <p className="mt-3 text-sm text-rose-700">{err}</p> : null}

      {!busy && !err && data ? (
        <div className="mt-4 space-y-3">
          <p className="text-xs text-slate-600">
            High-Risk-Systeme im Scope:{" "}
            <span className="font-semibold text-slate-900">{data.high_risk_system_count}</span>
            {data.per_system_critical.length > 0 ? (
              <>
                {" "}
                · Systeme mit roter KPI-Ampel:{" "}
                <span className="font-semibold text-rose-800">
                  {data.per_system_critical.length}
                </span>
              </>
            ) : null}
          </p>
          {top.length === 0 ? (
            <p className="text-sm text-slate-600">
              Noch keine KPI-Zeitreihen gepflegt – Werte je System unter{" "}
              <Link href="/tenant/ai-systems" className="font-semibold text-cyan-800 underline">
                KI-Register
              </Link>{" "}
              erfassen.
            </p>
          ) : (
            <ul className="divide-y divide-slate-100 rounded-xl border border-slate-200">
              {top.map((p) => (
                <li
                  key={p.kpi_key}
                  className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 text-sm"
                >
                  <div className="min-w-0">
                    <div className="font-medium text-slate-900">{p.name}</div>
                    <div className="text-xs text-slate-500">{p.kpi_key}</div>
                  </div>
                  <div className="flex items-center gap-3 tabular-nums">
                    <span className="text-slate-700">
                      Ø letzte Periode:{" "}
                      <span className="font-semibold">
                        {p.avg_latest != null ? p.avg_latest.toFixed(2) : "–"}
                      </span>{" "}
                      <span className="text-xs text-slate-500">{p.unit}</span>
                    </span>
                    <span className="text-lg text-slate-600" title={`Trend ${p.trend}`}>
                      {trendArrow(p.trend)}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </section>
  );
}
