"use client";

import Link from "next/link";
import React, { useMemo, useState } from "react";

import type { AIIncidentBySystem, AIIncidentOverview } from "@/lib/api";
import { CH_BTN_GHOST, CH_CARD, CH_SECTION_LABEL } from "@/lib/boardLayout";

function severityBadgeClass(severity: string): string {
  switch (severity) {
    case "high":
      return "bg-red-100 text-red-800 ring-red-200/60";
    case "medium":
      return "bg-amber-100 text-amber-900 ring-amber-200/60";
    case "low":
      return "bg-emerald-100 text-emerald-800 ring-emerald-200/60";
    default:
      return "bg-slate-100 text-slate-700 ring-slate-200/60";
  }
}

function severityLabel(severity: string): string {
  const labels: Record<string, string> = {
    low: "Niedrig",
    medium: "Mittel",
    high: "Hoch",
  };
  return labels[severity] ?? severity;
}

function severityIcon(severity: string): string {
  switch (severity) {
    case "high":
      return "🔴";
    case "medium":
      return "🟡";
    case "low":
      return "🟢";
    default:
      return "⚪";
  }
}

type Props = {
  overview: AIIncidentOverview;
  bySystem: AIIncidentBySystem[];
};

const MS_DAY = 86_400_000;

export function IncidentsBoardClient({ overview, bySystem }: Props) {
  const [windowDays, setWindowDays] = useState<string>("365");
  const [systemQuery, setSystemQuery] = useState("");
  const [severityFocus, setSeverityFocus] = useState<string>("all");

  const filteredRows = useMemo(() => {
    const q = systemQuery.trim().toLowerCase();
    const now = Date.now();
    const maxAge =
      windowDays === "all"
        ? null
        : Number.parseInt(windowDays, 10) * MS_DAY;

    return bySystem
      .filter((row) => {
        if (q) {
          const hay = `${row.ai_system_name} ${row.ai_system_id}`.toLowerCase();
          if (!hay.includes(q)) return false;
        }
        if (maxAge != null && row.last_incident_at) {
          const t = new Date(row.last_incident_at).getTime();
          if (Number.isFinite(t) && now - t > maxAge) return false;
        }
        return row.incident_count > 0;
      })
      .sort((a, b) => b.incident_count - a.incident_count);
  }, [bySystem, systemQuery, windowDays]);

  return (
    <div className="min-w-0 space-y-8">
      <section
        className={`${CH_CARD} border-slate-200/90 bg-white/95`}
        aria-label="Filter und Suche"
      >
        <p className={CH_SECTION_LABEL}>Filter</p>
        <p className="mt-1 text-xs text-slate-500">
          Zeitraum und System beziehen sich auf aggregierte Incidents je KI-System
          (API <code className="rounded bg-slate-100 px-1">/by-system</code>
          ). Schweregrad-Filter nutzt die Gesamtverteilung als Kontext.
        </p>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <label className="text-xs font-semibold text-slate-600" htmlFor="inc-window">
              Zeitraum (letztes Incident)
            </label>
            <select
              id="inc-window"
              className="mt-1.5 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 shadow-sm"
              value={windowDays}
              onChange={(e) => setWindowDays(e.target.value)}
            >
              <option value="30">Letzte 30 Tage</option>
              <option value="90">Letzte 90 Tage</option>
              <option value="365">Letzte 12 Monate</option>
              <option value="all">Alle</option>
            </select>
          </div>
          <div className="sm:col-span-2">
            <label className="text-xs font-semibold text-slate-600" htmlFor="inc-system-q">
              System / ID
            </label>
            <input
              id="inc-system-q"
              type="search"
              value={systemQuery}
              onChange={(e) => setSystemQuery(e.target.value)}
              placeholder="Name oder UUID filtern…"
              className="mt-1.5 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 shadow-sm placeholder:text-slate-400"
            />
          </div>
          <div>
            <span className="text-xs font-semibold text-slate-600">Schweregrad (Kontext)</span>
            <select
              className="mt-1.5 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 shadow-sm"
              value={severityFocus}
              onChange={(e) => setSeverityFocus(e.target.value)}
              aria-label="Schweregrad-Verteilung hervorheben"
            >
              <option value="all">Alle Stufen</option>
              <option value="high">Fokus: Hoch</option>
              <option value="medium">Fokus: Mittel</option>
              <option value="low">Fokus: Niedrig</option>
            </select>
          </div>
        </div>
      </section>

      <section aria-label="Incident-KPIs" className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <div className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Offen</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-slate-900">
            {overview.open_incidents}
          </p>
          <p className="mt-1 text-xs text-slate-500">Aktueller Bestand</p>
        </div>
        <div className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>MTTA</p>
          <p className="mt-2 text-2xl font-semibold tabular-nums text-slate-900">
            {overview.mean_time_to_ack_hours != null
              ? `~${overview.mean_time_to_ack_hours} h`
              : "–"}
          </p>
          <p className="mt-1 text-xs text-slate-500">Ø Zeit bis Bestätigung</p>
        </div>
        <div className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>MTTR</p>
          <p className="mt-2 text-2xl font-semibold tabular-nums text-slate-900">
            {overview.mean_time_to_recover_hours != null
              ? `~${overview.mean_time_to_recover_hours} h`
              : "–"}
          </p>
          <p className="mt-1 text-xs text-slate-500">Ø Recovery-Zeit</p>
        </div>
        <div className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>12 Monate gesamt</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-slate-900">
            {overview.total_incidents_last_12_months}
          </p>
          <p className="mt-1 text-xs text-slate-500">Rolling Window</p>
        </div>
      </section>

      <section aria-label="Verteilung Schweregrad" className={`${CH_CARD}`}>
        <h2 className="text-base font-semibold text-slate-900">Verteilung (12 Monate)</h2>
        {overview.by_severity.length === 0 ? (
          <p className="mt-3 text-sm text-slate-500">
            Keine Incidents in diesem Zeitraum erfasst.
          </p>
        ) : (
          <div className="mt-4 flex flex-wrap gap-2">
            {overview.by_severity.map((entry) => (
              <button
                key={entry.severity}
                type="button"
                onClick={() =>
                  setSeverityFocus((prev) =>
                    prev === entry.severity ? "all" : entry.severity,
                  )
                }
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-semibold ring-1 ring-inset transition ${
                  severityFocus === entry.severity
                    ? "ring-2 ring-cyan-500 " + severityBadgeClass(entry.severity)
                    : severityBadgeClass(entry.severity)
                }`}
              >
                <span aria-hidden>{severityIcon(entry.severity)}</span>
                {severityLabel(entry.severity)}: {entry.count}
              </button>
            ))}
          </div>
        )}
      </section>

      <section aria-label="KI-Systeme mit Incidents">
        <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
          <h2 className="text-base font-semibold text-slate-900">
            Systeme mit Vorfällen
          </h2>
          <span className="text-xs text-slate-500">
            {filteredRows.length} von {bySystem.length} Einträgen
          </span>
        </div>
        <div className="overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-md shadow-slate-200/50">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/90 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  <th className="px-4 py-3">System</th>
                  <th className="px-4 py-3">Anzahl</th>
                  <th className="px-4 py-3">Letztes Incident</th>
                  <th className="px-4 py-3 text-right">Aktionen</th>
                </tr>
              </thead>
              <tbody>
                {filteredRows.map((row) => (
                  <tr
                    key={row.ai_system_id}
                    className="border-b border-slate-100 transition hover:bg-cyan-50/50"
                  >
                    <td className="px-4 py-3">
                      <div className="font-semibold text-slate-900">{row.ai_system_name}</div>
                      <div className="text-xs text-slate-500">{row.ai_system_id}</div>
                    </td>
                    <td className="px-4 py-3 tabular-nums font-medium text-slate-800">
                      {row.incident_count}
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {row.last_incident_at
                        ? new Date(row.last_incident_at).toLocaleString("de-DE", {
                            dateStyle: "short",
                            timeStyle: "short",
                          })
                        : "–"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        href={`/tenant/ai-systems/${encodeURIComponent(row.ai_system_id)}`}
                        className={`${CH_BTN_GHOST} text-xs`}
                      >
                        System-Detail
                      </Link>
                    </td>
                  </tr>
                ))}
                {filteredRows.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-4 py-10 text-center text-sm text-slate-500">
                      Keine Systeme für die aktuellen Filter.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}
