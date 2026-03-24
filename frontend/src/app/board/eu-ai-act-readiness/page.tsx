import React from "react";
import Link from "next/link";

import {
  fetchEuAiActReadiness,
  type EUAIActReadinessOverview,
  type ReadinessRequirementTraffic,
} from "@/lib/api";

function aiSystemsFilterHref(systemIds: string[]): string {
  const q = systemIds.length
    ? `?ids=${encodeURIComponent(systemIds.slice(0, 100).join(","))}`
    : "";
  return `/tenant/ai-systems${q}`;
}

function trafficDot(traffic: ReadinessRequirementTraffic): string {
  switch (traffic) {
    case "red":
      return "bg-red-500";
    case "amber":
      return "bg-amber-400";
    default:
      return "bg-emerald-500";
  }
}

export default async function EuAiActReadinessPage() {
  let data: EUAIActReadinessOverview | null = null;
  try {
    data = await fetchEuAiActReadiness();
  } catch (error) {
    console.error("EU AI Act readiness API error:", error);
  }

  if (!data) {
    return (
      <main className="sbs-page-main">
        <header className="mb-6">
          <h1 className="sbs-h1">
            EU AI Act Readiness
          </h1>
        </header>
        <div
          role="status"
          className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800"
        >
          Readiness-Daten konnten nicht geladen werden.
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

  const readinessPct = Math.round(data.overall_readiness * 100);
  const q2done = data.days_remaining > 90;
  const q3done = data.days_remaining > 0 && data.overall_readiness >= 0.85;

  return (
    <main className="sbs-page-main">
      <header className="mb-6">
        <h1 className="sbs-h1">
          EU AI Act Readiness (High-Risk)
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Stichtag {data.deadline} · noch {data.days_remaining} Tage ·
          Gesamt-Readiness {readinessPct} %
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

      <section
        aria-label="Kernkennzahlen"
        className="mb-8 grid gap-4 md:grid-cols-3"
      >
        <div className="sbs-panel p-4">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Overall Readiness
          </h2>
          <p className="mt-2 text-3xl font-semibold text-slate-900">
            {readinessPct} %
          </p>
        </div>
        <div className="sbs-panel p-4">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            High-Risk mit essenziellen Controls
          </h2>
          <p className="mt-2 text-3xl font-semibold text-slate-900">
            {data.high_risk_systems_essential_complete}
          </p>
        </div>
        <div className="sbs-panel p-4">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            High-Risk mit Lücken
          </h2>
          <p className="mt-2 text-3xl font-semibold text-slate-900">
            {data.high_risk_systems_essential_incomplete}
          </p>
        </div>
      </section>

      <section
        aria-label="Roadmap"
        className="sbs-panel-muted mb-8 p-4"
      >
        <h2 className="text-sm font-semibold text-slate-800">
          Grobe Timeline bis Stichtag
        </h2>
        <ol className="mt-3 space-y-2 text-sm text-slate-700">
          <li className="flex items-center gap-2">
            <span
              className={`h-2 w-2 rounded-full ${q2done ? "bg-emerald-500" : "bg-slate-300"}`}
            />
            Q2 2026 – Fokus Lücken schließen (aktuell {readinessPct} % Readiness)
          </li>
          <li className="flex items-center gap-2">
            <span
              className={`h-2 w-2 rounded-full ${q3done ? "bg-emerald-500" : "bg-slate-300"}`}
            />
            Q3 2026 – Ziel ≥ 85 % Readiness vor Frist
          </li>
        </ol>
      </section>

      <section className="mb-8" aria-label="Kritische Anforderungen">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-600">
          Top Critical Requirements
        </h2>
        {data.critical_requirements.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">
            Keine priorisierten Lücken aus dem Compliance-Register.
          </p>
        ) : (
          <ul className="mt-3 space-y-2">
            {data.critical_requirements.map((r) => (
              <li
                key={r.requirement_id ?? `${r.code}-${r.name}`}
                className="sbs-panel flex items-start gap-3 px-3 py-2 text-sm"
              >
                <span
                  className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${trafficDot(r.traffic)}`}
                  title={r.traffic}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                    <span className="font-medium text-slate-900">
                      {r.code}: {r.name}
                    </span>
                    <span className="text-slate-500">
                      {r.affected_systems_count} Systeme · Prio {r.priority}
                    </span>
                    {(r.open_actions_count_for_requirement ?? 0) > 0 ? (
                      <span
                        className="inline-flex rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-900"
                        title="Offene oder laufende Maßnahmen mit Bezug zu dieser Anforderung"
                      >
                        {r.open_actions_count_for_requirement} Maßnahme
                        {(r.open_actions_count_for_requirement ?? 0) === 1 ? "" : "n"}
                      </span>
                    ) : null}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs">
                    {(r.related_ai_system_ids?.length ?? 0) > 0 ? (
                      <Link
                        href={aiSystemsFilterHref(r.related_ai_system_ids ?? [])}
                        className="font-medium text-slate-600 underline hover:text-slate-900"
                      >
                        Zu den betroffenen Systemen
                      </Link>
                    ) : null}
                    <Link
                      href="/board/eu-ai-act-readiness#governance-actions"
                      className="font-medium text-slate-600 underline hover:text-slate-900"
                    >
                      Maßnahmen ansehen
                    </Link>
                    <Link
                      href="/board/eu-ai-act-readiness#governance-actions"
                      className="font-medium text-slate-600 underline hover:text-slate-900"
                      title="Neue Einträge z. B. über POST /api/v1/ai-governance/actions oder Ihr ITSM"
                    >
                      Maßnahme erfassen
                    </Link>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="mb-8" aria-label="Vorgeschlagene Maßnahmen">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-600">
          Vorgeschlagene Maßnahmen (nicht persistiert)
        </h2>
        {data.suggested_actions.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">
            Keine automatischen Vorschläge – oder alle Fokus-Systeme vollständig.
          </p>
        ) : (
          <ul className="mt-3 space-y-2 text-sm text-slate-700">
            {data.suggested_actions.map((s, i) => (
              <li
                key={`${s.title}-${i}`}
                className="sbs-panel-muted border border-dashed border-[var(--sbs-border)] px-3 py-2"
              >
                <span className="font-medium">{s.title}</span>
                <span className="ml-2 text-xs text-slate-500">
                  {s.related_requirement} · Prio {s.suggested_priority}
                </span>
                <p className="mt-1 text-xs text-slate-600">{s.rationale}</p>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section id="governance-actions" aria-label="Offene Maßnahmen">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-600">
          Offene Maßnahmen
        </h2>
        {data.open_governance_actions.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">
            Keine offenen Einträge in{" "}
            <code className="rounded bg-slate-100 px-1">ai_governance_actions</code>.
          </p>
        ) : (
          <ul className="sbs-panel mt-3 divide-y divide-[var(--sbs-border)] overflow-hidden p-0">
            {data.open_governance_actions.map((a) => (
              <li key={a.id} className="px-4 py-3 text-sm">
                <div className="font-medium text-slate-900">{a.title}</div>
                <div className="mt-1 text-xs text-slate-500">
                  {a.related_requirement} · {a.status}
                  {a.due_date
                    ? ` · Fällig ${new Date(a.due_date).toLocaleDateString("de-DE")}`
                    : ""}
                </div>
                {a.related_ai_system_id ? (
                  <Link
                    href="/tenant/eu-ai-act"
                    className="mt-1 inline-block text-xs font-medium text-slate-600 underline hover:text-slate-900"
                  >
                    KI-System {a.related_ai_system_id} (EU-AI-Act-Ansicht)
                  </Link>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
