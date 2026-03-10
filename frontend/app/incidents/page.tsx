import React from "react";

type IncidentSeverity = "low" | "medium" | "high" | "critical";
type IncidentStatus = "open" | "in_progress" | "resolved";

interface Incident {
  id: string;
  ai_system_id: string | null;
  title: string;
  severity: IncidentSeverity;
  status: IncidentStatus;
  created_at: string;
  updated_at: string;
  actor: string | null;
  source: string | null;
  summary: string | null;
}

async function fetchIncidents(): Promise<Incident[]> {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
  const apiKey = process.env.NEXT_PUBLIC_DEMO_API_KEY ?? "";

  const res = await fetch(`${base}/api/v1/incidents/timeline?limit=50`, {
    cache: "no-store",
    headers: { Authorization: `Bearer ${apiKey}` },
  });

  if (!res.ok) {
    // Graceful degradation – leere Liste statt Crash
    console.error("Incidents API error:", res.status);
    return [];
  }

  return res.json() as Promise<Incident[]>;
}

function severityDot(severity: IncidentSeverity): string {
  const map: Record<IncidentSeverity, string> = {
    critical: "bg-red-600 ring-red-200",
    high: "bg-red-400 ring-red-100",
    medium: "bg-amber-400 ring-amber-100",
    low: "bg-emerald-400 ring-emerald-100",
  };
  return map[severity];
}

function statusBadge(status: IncidentStatus): string {
  const map: Record<IncidentStatus, string> = {
    open: "bg-red-50 text-red-700 ring-1 ring-red-200",
    in_progress: "bg-amber-50 text-amber-700 ring-1 ring-amber-200",
    resolved: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200",
  };
  return map[status];
}

function severityBadge(severity: IncidentSeverity): string {
  const map: Record<IncidentSeverity, string> = {
    critical: "bg-red-100 text-red-800",
    high: "bg-orange-100 text-orange-800",
    medium: "bg-amber-100 text-amber-800",
    low: "bg-slate-100 text-slate-600",
  };
  return map[severity];
}

export default async function IncidentsPage() {
  const incidents = await fetchIncidents();

  const total = incidents.length;
  const open = incidents.filter((i) => i.status === "open").length;
  const inProgress = incidents.filter((i) => i.status === "in_progress").length;
  const resolved = incidents.filter((i) => i.status === "resolved").length;
  const criticalOpen = incidents.filter(
    (i) => i.status === "open" && i.severity === "critical"
  ).length;
  const highOpen = incidents.filter(
    (i) => i.status === "open" && i.severity === "high"
  ).length;

  const kpis = [
    { label: "Open", value: open, color: "text-red-600" },
    { label: "In Progress", value: inProgress, color: "text-amber-600" },
    { label: "Resolved", value: resolved, color: "text-emerald-600" },
    { label: "Critical Open", value: criticalOpen, color: "text-red-700" },
    { label: "High Open", value: highOpen, color: "text-orange-600" },
    { label: "Total", value: total, color: "text-slate-700" },
  ];

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">AI Incident Monitor</h1>
        <p className="mt-1 text-sm text-slate-500">
          EU AI Act Art. 73 · NIS2 Incident Reporting · ISO 42001 Post-Market Surveillance
        </p>
      </div>

      {/* KPI Header */}
      <div className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        {kpis.map((kpi) => (
          <div
            key={kpi.label}
            className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm"
          >
            <div className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
              {kpi.label}
            </div>
            <div className={`mt-1 text-3xl font-bold ${kpi.color}`}>{kpi.value}</div>
          </div>
        ))}
      </div>

      {/* Timeline */}
      <div className="rounded-xl border border-slate-100 bg-white p-6 shadow-sm">
        <h2 className="mb-6 text-base font-semibold text-slate-800">Incident Timeline</h2>

        {incidents.length === 0 ? (
          <div className="flex flex-col items-center py-12 text-center">
            <div className="mb-3 text-4xl">✅</div>
            <p className="text-sm font-medium text-slate-700">Keine Incidents vorhanden</p>
            <p className="mt-1 text-xs text-slate-400">
              Dein EU AI Act / NIS2 Setup ist aktuell sauber.
            </p>
          </div>
        ) : (
          <ol className="relative border-l border-slate-200">
            {incidents.map((incident) => (
              <li key={incident.id} className="mb-8 ml-6">
                {/* Timeline Dot */}
                <span
                  className={`absolute -left-[9px] flex h-4 w-4 items-center justify-center rounded-full ring-4 ring-white ${
                    severityDot(incident.severity)
                  }`}
                />

                {/* Timestamp */}
                <time className="mb-1 block text-xs font-mono text-slate-400">
                  {new Date(incident.created_at).toLocaleString("de-DE", {
                    dateStyle: "medium",
                    timeStyle: "short",
                  })}
                </time>

                {/* Title + Badges */}
                <div className="mb-1 flex flex-wrap items-center gap-2">
                  <span className="text-sm font-semibold text-slate-900">
                    {incident.title}
                  </span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
                      statusBadge(incident.status)
                    }`}
                  >
                    {incident.status.replace("_", " ").toUpperCase()}
                  </span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
                      severityBadge(incident.severity)
                    }`}
                  >
                    {incident.severity.toUpperCase()}
                  </span>
                </div>

                {/* Summary */}
                {incident.summary && (
                  <p className="mb-2 text-sm text-slate-600">{incident.summary}</p>
                )}

                {/* Meta */}
                <div className="flex flex-wrap gap-3 text-[11px] text-slate-400">
                  {incident.ai_system_id && (
                    <span>AI-System: <code className="font-mono">{incident.ai_system_id}</code></span>
                  )}
                  {incident.source && <span>Source: {incident.source}</span>}
                  {incident.actor && <span>Actor: {incident.actor}</span>}
                </div>
              </li>
            ))}
          </ol>
        )}
      </div>
    </main>
  );
}
