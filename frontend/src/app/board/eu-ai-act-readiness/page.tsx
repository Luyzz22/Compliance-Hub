import React from "react";
import Link from "next/link";

import {
  fetchEuAiActReadiness,
  type EUAIActReadinessOverview,
  type ReadinessRequirementTraffic,
} from "@/lib/api";

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
      <main className="mx-auto max-w-6xl px-4 py-8">
        <header className="mb-6">
          <h1 className="text-2xl font-bold text-slate-900">
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
    <main className="mx-auto max-w-6xl px-4 py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">
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
        <div className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Overall Readiness
          </h2>
          <p className="mt-2 text-3xl font-semibold text-slate-900">
            {readinessPct} %
          </p>
        </div>
        <div className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            High-Risk mit essenziellen Controls
          </h2>
          <p className="mt-2 text-3xl font-semibold text-slate-900">
            {data.high_risk_systems_essential_complete}
          </p>
        </div>
        <div className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
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
        className="mb-8 rounded-xl border border-slate-100 bg-slate-50 p-4"
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
                key={`${r.code}-${r.name}`}
                className="flex items-start gap-3 rounded-lg border border-slate-100 bg-white px-3 py-2 text-sm shadow-sm"
              >
                <span
                  className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${trafficDot(r.traffic)}`}
                  title={r.traffic}
                />
                <div>
                  <span className="font-medium text-slate-900">
                    {r.code}: {r.name}
                  </span>
                  <span className="ml-2 text-slate-500">
                    {r.affected_systems_count} Systeme · Prio {r.priority}
                  </span>
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
                className="rounded-lg border border-dashed border-slate-200 bg-white px-3 py-2"
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

      <section aria-label="Offene Maßnahmen">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-600">
          Offene Maßnahmen
        </h2>
        {data.open_governance_actions.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">
            Keine offenen Einträge in{" "}
            <code className="rounded bg-slate-100 px-1">ai_governance_actions</code>.
          </p>
        ) : (
          <ul className="mt-3 divide-y divide-slate-100 rounded-xl border border-slate-100 bg-white shadow-sm">
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
