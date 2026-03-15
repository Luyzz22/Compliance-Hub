import React from "react";
import Link from "next/link";

import {
  fetchIncidentOverview,
  fetchIncidentsBySystem,
  type AIIncidentBySystem,
  type AIIncidentOverview,
} from "@/lib/api";

function severityBadgeClass(severity: string): string {
  switch (severity) {
    case "high":
      return "bg-red-100 text-red-800";
    case "medium":
      return "bg-amber-100 text-amber-800";
    case "low":
      return "bg-emerald-100 text-emerald-800";
    default:
      return "bg-slate-100 text-slate-700";
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
      <main className="mx-auto max-w-6xl px-4 py-8">
        <header className="mb-6">
          <h1 className="text-2xl font-bold text-slate-900">
            AI Governance – Incident-Übersicht
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            NIS2 Art. 21/23 · ISO 42001 Incident Management
          </p>
        </header>
        <div
          role="status"
          className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800"
        >
          Incident-KPIs konnten nicht geladen werden. Bitte versuchen Sie es
          später erneut oder wenden Sie sich an das AI-Governance-Team.
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

  const topSystems = bySystem.slice(0, 3);

  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">
          AI Governance – Incident-Übersicht
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          NIS2 Art. 21/23 (Incident & Business Continuity) · ISO 42001 Incident
          Management · Standort Deutschland
        </p>
        <p className="mt-2">
          <Link
            href="/board/kpis"
            className="text-sm font-medium text-slate-600 underline hover:text-slate-900"
            aria-label="Zurück zu Board-KPIs"
          >
            ← Zurück zu Board-KPIs
          </Link>
        </p>
      </header>

      <section
        aria-label="Incident-KPIs"
        className="mb-8 grid gap-4 md:grid-cols-2 lg:grid-cols-4"
      >
        <div className="flex flex-col rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Incidents letzte 12 Monate
          </h2>
          <p className="mt-2 text-3xl font-semibold text-slate-900">
            {overview.total_incidents_last_12_months}
          </p>
          <p className="mt-1 text-xs text-slate-500">Gesamt (Rolling 12 Monate)</p>
        </div>
        <div className="flex flex-col rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Aktuell offene Incidents
          </h2>
          <p className="mt-2 text-3xl font-semibold text-slate-900">
            {overview.open_incidents}
          </p>
          <p className="mt-1 text-xs text-slate-500">Status: offen</p>
        </div>
        <div className="flex flex-col rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Major Incidents (NIS2-relevant)
          </h2>
          <p className="mt-2 text-3xl font-semibold text-slate-900">
            {overview.major_incidents_last_12_months}
          </p>
          <p className="mt-1 text-xs text-slate-500">Schweregrad Hoch, 12 Monate</p>
        </div>
        <div className="flex flex-col rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            MTTA / MTTR
          </h2>
          <p className="mt-2 text-lg font-semibold text-slate-900">
            {overview.mean_time_to_ack_hours != null
              ? `~${overview.mean_time_to_ack_hours} h`
              : "–"}{" "}
            /{" "}
            {overview.mean_time_to_recover_hours != null
              ? `~${overview.mean_time_to_recover_hours} h`
              : "–"}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Ø Zeit bis Bestätigung / Wiederherstellung
          </p>
        </div>
      </section>

      <section
        aria-label="Incidents nach Schweregrad"
        className="mb-8 rounded-xl border border-slate-100 bg-white p-4 shadow-sm"
      >
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-700">
          Incidents nach Schweregrad
        </h2>
        {overview.by_severity.length === 0 ? (
          <p className="text-sm text-slate-500">
            In den letzten 12 Monaten keine Incidents erfasst.
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {overview.by_severity.map((entry) => (
              <span
                key={entry.severity}
                className={`rounded-full px-3 py-1 text-sm font-medium ${severityBadgeClass(entry.severity)}`}
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
          className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm"
        >
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-700">
            Top 3 KI-Systeme mit den meisten Incidents (12 Monate)
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-xs text-slate-500">
                  <th className="pb-2 font-semibold">KI-System</th>
                  <th className="pb-2 font-semibold">Anzahl Incidents</th>
                  <th className="pb-2 font-semibold">Letztes Incident</th>
                </tr>
              </thead>
              <tbody>
                {topSystems.map((row) => (
                  <tr key={row.ai_system_id} className="border-b border-slate-100">
                    <td className="py-2 font-medium text-slate-900">
                      {row.ai_system_name}
                    </td>
                    <td className="py-2 text-slate-700">{row.incident_count}</td>
                    <td className="py-2 text-slate-600">
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
    </main>
  );
}
