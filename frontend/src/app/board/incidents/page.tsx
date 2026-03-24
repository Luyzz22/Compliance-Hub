import React from "react";
import Link from "next/link";

import {
  fetchIncidentOverview,
  fetchIncidentsBySystem,
  type AIIncidentBySystem,
  type AIIncidentOverview,
} from "@/lib/api";
import {
  BOARD_PAGE_ROOT_CLASS,
  CH_CARD,
  CH_PAGE_SUB,
  CH_PAGE_TITLE,
  CH_SECTION_LABEL,
} from "@/lib/boardLayout";

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

export default async function BoardIncidentsPage() {
  let overview: AIIncidentOverview | null = null;
  let bySystem: AIIncidentBySystem[] = [];

  try {
    overview = await fetchIncidentOverview();
  } catch (error) {
    console.error("Incident overview API error:", error);
  }

  if (overview) {
    try {
      bySystem = await fetchIncidentsBySystem();
    } catch (error) {
      console.error("Incidents by system API error:", error);
    }
  }

  if (!overview) {
    return (
      <div className={BOARD_PAGE_ROOT_CLASS}>
        <header className="mb-8">
          <h1 className={CH_PAGE_TITLE}>Incidents</h1>
          <p className={CH_PAGE_SUB}>
            NIS2 Art. 21/23 · ISO 42001 Incident Management
          </p>
        </header>
        <div
          role="status"
          className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
        >
          Incident-KPIs konnten nicht geladen werden. Bitte versuchen Sie es
          später erneut oder wenden Sie sich an das AI-Governance-Team.
        </div>
        <p className="mt-4">
          <Link
            href="/board/kpis"
            className="text-sm font-semibold text-cyan-700 underline decoration-cyan-700/30 hover:text-cyan-900"
          >
            ← Zurück zu Board-KPIs
          </Link>
        </p>
      </div>
    );
  }

  const topSystems = bySystem.slice(0, 3);

  return (
    <div className={BOARD_PAGE_ROOT_CLASS}>
      <header className="mb-8">
        <h1 className={CH_PAGE_TITLE}>Incidents</h1>
        <p className={CH_PAGE_SUB}>
          NIS2 Art. 21/23 (Incident &amp; Business Continuity) · ISO 42001 ·
          Standort Deutschland
        </p>
        <p className="mt-3">
          <Link
            href="/board/kpis"
            className="text-sm font-semibold text-cyan-700 underline decoration-cyan-700/30 hover:text-cyan-900"
            aria-label="Zurück zu Board-KPIs"
          >
            ← Zurück zu Board-KPIs
          </Link>
        </p>
      </header>

      <div
        className="mb-8 flex flex-wrap items-end gap-3 rounded-2xl border border-slate-200/90 bg-white/90 p-4 shadow-sm"
        aria-label="Filter (Demonstration)"
      >
        <div className="min-w-[12rem] flex-1">
          <label className="text-xs font-semibold text-slate-500" htmlFor="inc-search">
            Suche
          </label>
          <input
            id="inc-search"
            type="search"
            placeholder="KI-System, ID…"
            disabled
            title="Demonstrativ – keine Filterlogik"
            className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600 opacity-80"
          />
        </div>
        <div className="w-full min-w-[10rem] sm:w-48">
          <span className="text-xs font-semibold text-slate-500">Schweregrad</span>
          <select
            disabled
            title="Demonstrativ"
            className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600 opacity-80"
            defaultValue="all"
          >
            <option value="all">Alle</option>
            <option value="high">Hoch</option>
            <option value="medium">Mittel</option>
            <option value="low">Niedrig</option>
          </select>
        </div>
      </div>

      <section
        aria-label="Incident-KPIs"
        className="mb-8 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4"
      >
        <div className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Offene Incidents</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-slate-900">
            {overview.open_incidents}
          </p>
          <p className="mt-1 text-xs text-slate-500">Aktueller Bestand</p>
        </div>
        <div className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>12 Monate</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-slate-900">
            {overview.total_incidents_last_12_months}
          </p>
          <p className="mt-1 text-xs text-slate-500">Gesamt (Rolling)</p>
        </div>
        <div className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Major (NIS2)</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-slate-900">
            {overview.major_incidents_last_12_months}
          </p>
          <p className="mt-1 text-xs text-slate-500">Schweregrad hoch</p>
        </div>
        <div className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>MTTA / MTTR</p>
          <p className="mt-2 text-lg font-semibold tabular-nums text-slate-900">
            {overview.mean_time_to_ack_hours != null
              ? `~${overview.mean_time_to_ack_hours} h`
              : "–"}{" "}
            <span className="text-slate-400">/</span>{" "}
            {overview.mean_time_to_recover_hours != null
              ? `~${overview.mean_time_to_recover_hours} h`
              : "–"}
          </p>
          <p className="mt-1 text-xs text-slate-500">Ø Bestätigung / Recovery</p>
        </div>
      </section>

      <section aria-label="Incidents nach Schweregrad" className={`${CH_CARD} mb-8`}>
        <h2 className="text-base font-semibold text-slate-900">Nach Schweregrad</h2>
        {overview.by_severity.length === 0 ? (
          <p className="mt-3 text-sm text-slate-500">
            In den letzten 12 Monaten keine Incidents erfasst.
          </p>
        ) : (
          <div className="mt-4 flex flex-wrap gap-2">
            {overview.by_severity.map((entry) => (
              <span
                key={entry.severity}
                className={`inline-flex rounded-full px-3 py-1 text-sm font-semibold ring-1 ring-inset ${severityBadgeClass(entry.severity)}`}
              >
                {severityLabel(entry.severity)}: {entry.count}
              </span>
            ))}
          </div>
        )}
      </section>

      {topSystems.length > 0 && (
        <section
          aria-label="Top-KI-Systeme nach Incident-Anzahl"
          className={CH_CARD}
        >
          <h2 className="text-base font-semibold text-slate-900">
            Top 3 KI-Systeme (12 Monate)
          </h2>
          <div className="mt-4 overflow-x-auto rounded-xl border border-slate-100">
            <table className="w-full min-w-[320px] text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/80 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  <th className="px-4 py-3">KI-System</th>
                  <th className="px-4 py-3">Anzahl</th>
                  <th className="px-4 py-3">Letztes Incident</th>
                </tr>
              </thead>
              <tbody>
                {topSystems.map((row) => (
                  <tr
                    key={row.ai_system_id}
                    className="border-b border-slate-100 transition hover:bg-cyan-50/40"
                  >
                    <td className="px-4 py-3 font-semibold text-slate-900">
                      {row.ai_system_name}
                    </td>
                    <td className="px-4 py-3 tabular-nums text-slate-700">
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
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
