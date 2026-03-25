"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";

import {
  fetchTenantAiSystemKpis,
  postTenantAiSystemKpi,
  type AiSystemKpiSeriesDto,
} from "@/lib/api";
import { CH_BTN_PRIMARY, CH_BTN_SECONDARY, CH_SECTION_LABEL } from "@/lib/boardLayout";

function trendArrow(t: string): string {
  if (t === "up") return "↑";
  if (t === "down") return "↓";
  return "→";
}

function MiniSparkline({ values }: { values: number[] }) {
  if (values.length < 2) return <span className="text-xs text-slate-400">—</span>;
  const w = 72;
  const h = 22;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w;
    const y = h - ((v - min) / span) * (h - 4) - 2;
    return `${x},${y}`;
  });
  return (
    <svg width={w} height={h} className="inline-block text-cyan-700" aria-hidden>
      <polyline
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        points={pts.join(" ")}
      />
    </svg>
  );
}

export function AiSystemKpiPanel({ tenantId, systemId }: { tenantId: string; systemId: string }) {
  const [series, setSeries] = useState<AiSystemKpiSeriesDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [defId, setDefId] = useState("");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const [valueStr, setValueStr] = useState("");
  const [comment, setComment] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const res = await fetchTenantAiSystemKpis(tenantId, systemId);
      setSeries(res.series);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Laden fehlgeschlagen");
      setSeries([]);
    } finally {
      setLoading(false);
    }
  }, [tenantId, systemId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    setDefId("");
  }, [systemId]);

  useEffect(() => {
    if (series.length > 0 && !defId) {
      setDefId(series[0].definition.id);
    }
  }, [series, defId]);

  const sortedSeries = useMemo(
    () => [...series].sort((a, b) => a.definition.key.localeCompare(b.definition.key)),
    [series],
  );

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const val = Number(valueStr.replace(",", "."));
    if (!defId || !periodStart || !periodEnd || Number.isNaN(val)) return;
    setSaving(true);
    try {
      const ps = new Date(periodStart).toISOString();
      const pe = new Date(periodEnd).toISOString();
      await postTenantAiSystemKpi(tenantId, systemId, {
        kpi_definition_id: defId,
        period_start: ps,
        period_end: pe,
        value: val,
        source: "manual",
        comment: comment.trim() || null,
      });
      setComment("");
      setValueStr("");
      await load();
    } catch (er) {
      setErr(er instanceof Error ? er.message : "Speichern fehlgeschlagen");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div data-testid="ai-system-kpi-panel">
      {loading ? <p className="text-sm text-slate-500">Lade KPIs…</p> : null}
      {err ? <p className="text-sm text-rose-700">{err}</p> : null}

      {!loading && !err ? (
        <form
          onSubmit={(e) => void submit(e)}
          className="mb-6 rounded-xl border border-slate-200 bg-slate-50/60 p-4"
        >
          <p className={CH_SECTION_LABEL}>Wert erfassen / aktualisieren</p>
          <p className="mt-1 text-xs text-slate-600">
            Pro KPI und Periodenbeginn (Upsert). Zeitraum z. B. Quartalsgrenzen.
          </p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <label className="block text-xs font-medium text-slate-600">
              KPI
              <select
                className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-2 py-2 text-sm"
                value={defId}
                onChange={(e) => setDefId(e.target.value)}
              >
                {sortedSeries.map((s) => (
                  <option key={s.definition.id} value={s.definition.id}>
                    {s.definition.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-xs font-medium text-slate-600">
              Periodenstart
              <input
                type="datetime-local"
                className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-2 py-2 text-sm"
                value={periodStart}
                onChange={(e) => setPeriodStart(e.target.value)}
                required
              />
            </label>
            <label className="block text-xs font-medium text-slate-600">
              Periodenende
              <input
                type="datetime-local"
                className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-2 py-2 text-sm"
                value={periodEnd}
                onChange={(e) => setPeriodEnd(e.target.value)}
                required
              />
            </label>
            <label className="block text-xs font-medium text-slate-600">
              Wert (numerisch)
              <input
                type="text"
                inputMode="decimal"
                className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-2 py-2 text-sm"
                value={valueStr}
                onChange={(e) => setValueStr(e.target.value)}
                placeholder="z. B. 2.5"
                required
              />
            </label>
          </div>
          <label className="mt-3 block text-xs font-medium text-slate-600">
            Kommentar (optional)
            <input
              type="text"
              className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-2 py-2 text-sm"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
            />
          </label>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="submit"
              className={`${CH_BTN_PRIMARY} text-sm`}
              disabled={saving || sortedSeries.length === 0}
            >
              {saving ? "Speichern…" : "Speichern"}
            </button>
            <button
              type="button"
              className={`${CH_BTN_SECONDARY} text-sm`}
              onClick={() => void load()}
              disabled={saving}
            >
              Aktualisieren
            </button>
          </div>
        </form>
      ) : null}

      <div className="space-y-4">
        {sortedSeries.map((s) => {
          const asc = [...s.periods].sort(
            (a, b) => new Date(a.period_start).getTime() - new Date(b.period_start).getTime(),
          );
          const vals = asc.map((p) => p.value);
          const latest = s.periods[0];
          return (
            <div
              key={s.definition.id}
              className="rounded-xl border border-slate-200/90 bg-white px-4 py-3"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <h3 className="text-sm font-semibold text-slate-900">{s.definition.name}</h3>
                  <p className="mt-1 text-xs text-slate-600 line-clamp-2">{s.definition.description}</p>
                  <p className="mt-1 text-[11px] text-slate-500">
                    {s.definition.key} · {s.definition.unit} · Zielrichtung{" "}
                    {s.definition.recommended_direction}
                  </p>
                </div>
                <div className="flex items-center gap-2 text-right">
                  <MiniSparkline values={vals} />
                  <div>
                    <div className="text-lg font-semibold tabular-nums text-slate-900">
                      {latest ? latest.value : "–"}{" "}
                      <span className="text-xs font-normal text-slate-500">{s.definition.unit}</span>
                    </div>
                    <div className="text-xs text-slate-600">
                      Trend {trendArrow(s.trend)}{" "}
                      <span
                        className={
                          s.latest_status === "red" ? "font-semibold text-rose-700" : "text-emerald-700"
                        }
                      >
                        {s.latest_status === "red" ? "Ampel rot" : "OK"}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
