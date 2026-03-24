import React from "react";
import Link from "next/link";

import {
  fetchEuAiActReadiness,
  type EUAIActReadinessOverview,
  type ReadinessRequirementTraffic,
} from "@/lib/api";
import {
  BOARD_PAGE_ROOT_CLASS,
  CH_CARD,
  CH_PAGE_SUB,
  CH_PAGE_TITLE,
  CH_SECTION_LABEL,
  CH_BTN_PRIMARY,
  CH_BTN_SECONDARY,
} from "@/lib/boardLayout";

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

function trafficLabel(traffic: ReadinessRequirementTraffic): string {
  switch (traffic) {
    case "red":
      return "Rot";
    case "amber":
      return "Gelb";
    default:
      return "Grün";
  }
}

function requirementGapSummary(traffic: ReadinessRequirementTraffic): string {
  switch (traffic) {
    case "red":
      return "Wesentliche Controls oder Nachweise fehlen – Umsetzung vor Stichtag priorisieren.";
    case "amber":
      return "Teilweise umgesetzt; offene Punkte und Evidenzen zeitnah schließen.";
    default:
      return "Stand tragfähig; fortlaufende Pflege und Stichproben empfohlen.";
  }
}

function ReadinessRing({ percent }: { percent: number }) {
  const p = Math.min(100, Math.max(0, percent));
  return (
    <div
      className="relative mx-auto h-36 w-36 shrink-0"
      aria-hidden
    >
      <div
        className="absolute inset-0 rounded-full"
        style={{
          background: `conic-gradient(rgb(8 145 178) 0% ${p}%, rgb(226 232 240) ${p}% 100%)`,
        }}
      />
      <div className="absolute inset-[12px] flex flex-col items-center justify-center rounded-full bg-white shadow-inner">
        <span className="text-3xl font-semibold tabular-nums text-slate-900">{p}%</span>
        <span className="text-[0.65rem] font-medium uppercase tracking-wide text-slate-500">
          Readiness
        </span>
      </div>
    </div>
  );
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
      <div className={BOARD_PAGE_ROOT_CLASS}>
        <header className="mb-8">
          <h1 className={CH_PAGE_TITLE}>EU AI Act Readiness</h1>
          <p className={CH_PAGE_SUB}>High-Risk-Systeme bis 02.08.2026</p>
        </header>
        <div
          role="status"
          className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
        >
          Readiness-Daten konnten nicht geladen werden.
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

  const readinessPct = Math.round(data.overall_readiness * 100);
  const q2done = data.days_remaining > 90;
  const q3done = data.days_remaining > 0 && data.overall_readiness >= 0.85;

  return (
    <div className={BOARD_PAGE_ROOT_CLASS}>
      <header className="mb-8">
        <h1 className={CH_PAGE_TITLE}>EU AI Act Readiness</h1>
        <p className={CH_PAGE_SUB}>
          High-Risk-Systeme bis{" "}
          <time dateTime="2026-08-02">02.08.2026</time>
          {" · "}
          noch {data.days_remaining} Tage · Gesamt {readinessPct}%
        </p>
        <p className="mt-3">
          <Link
            href="/board/kpis"
            className="text-sm font-semibold text-cyan-700 underline decoration-cyan-700/30 hover:text-cyan-900"
          >
            ← Zurück zu Board-KPIs
          </Link>
        </p>
      </header>

      <section className={`${CH_CARD} mb-8`} aria-label="Readiness-Übersicht">
        <div className="grid gap-8 lg:grid-cols-[auto_1fr] lg:items-center">
          <div className="text-center lg:text-left">
            <ReadinessRing percent={readinessPct} />
            <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Gesamt-Readiness
            </p>
          </div>
          <div className="min-w-0 space-y-6">
            <div>
              <p className={CH_SECTION_LABEL}>Fortschritt</p>
              <div className="mt-2 h-3 overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-cyan-600 to-teal-500 transition-all"
                  style={{ width: `${readinessPct}%` }}
                />
              </div>
              <p className="mt-2 text-sm text-slate-600">
                Ziel empfohlen: ≥ 85&nbsp;% vor Stichtag.
              </p>
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div className="rounded-xl border border-amber-100 bg-amber-50/70 p-4">
                <p className="text-xs font-medium text-amber-900/80">Tage bis 02.08.2026</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums text-amber-950">
                  {data.days_remaining}
                </p>
                <p className="mt-1 text-[0.7rem] text-amber-900/70">
                  Vollanwendung High-Risk (EU AI Act)
                </p>
              </div>
              <div className="rounded-xl border border-slate-100 bg-slate-50/80 p-4">
                <p className="text-xs font-medium text-slate-500">HR + Controls komplett</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">
                  {data.high_risk_systems_essential_complete}
                </p>
              </div>
              <div className="rounded-xl border border-slate-100 bg-slate-50/80 p-4">
                <p className="text-xs font-medium text-slate-500">HR mit Lücken</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">
                  {data.high_risk_systems_essential_incomplete}
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section aria-label="Roadmap" className={`${CH_CARD} mb-8`}>
        <h2 className="text-base font-semibold text-slate-900">Roadmap bis Stichtag</h2>
        <ol className="mt-4 space-y-3 text-sm text-slate-700">
          <li className="flex items-start gap-3">
            <span
              className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${q2done ? "bg-emerald-500" : "bg-slate-300"}`}
            />
            Q2 2026 – Lücken schließen (aktuell {readinessPct}% Readiness)
          </li>
          <li className="flex items-start gap-3">
            <span
              className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${q3done ? "bg-emerald-500" : "bg-slate-300"}`}
            />
            Q3 2026 – Ziel ≥ 85&nbsp;% Readiness vor Frist
          </li>
        </ol>
      </section>

      <section className="mb-8" aria-label="Kritische Anforderungen">
        <h2 className={`${CH_SECTION_LABEL} mb-4`}>Top Critical Requirements</h2>
        {data.critical_requirements.length === 0 ? (
          <p className="text-sm text-slate-500">
            Keine priorisierten Lücken aus dem Compliance-Register.
          </p>
        ) : (
          <ul className="space-y-3">
            {data.critical_requirements.map((r) => (
              <li
                key={r.requirement_id ?? `${r.code}-${r.name}`}
                className={`${CH_CARD} flex min-w-0 flex-col gap-4 sm:flex-row sm:items-start`}
              >
                <div className="flex shrink-0 items-center gap-2">
                  <span
                    className={`h-3 w-3 rounded-full ${trafficDot(r.traffic)}`}
                    title={r.traffic}
                  />
                  <span className="text-xs font-semibold text-slate-600">
                    {trafficLabel(r.traffic)}
                  </span>
                </div>
                <div className="min-w-0 flex-1">
                  <div className="font-semibold text-slate-900">
                    {r.code}: {r.name}
                  </div>
                  <p className="mt-1 text-sm text-slate-600">
                    {r.affected_systems_count} Systeme · Priorität {r.priority}
                  </p>
                  <p className="mt-2 text-sm leading-relaxed text-slate-600">
                    {requirementGapSummary(r.traffic)}
                  </p>
                  {(r.open_actions_count_for_requirement ?? 0) > 0 ? (
                    <span className="mt-2 inline-flex rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-semibold text-indigo-900">
                      {r.open_actions_count_for_requirement} offene Maßnahme
                      {(r.open_actions_count_for_requirement ?? 0) === 1 ? "" : "n"}
                    </span>
                  ) : null}
                  <div className="mt-3 flex flex-wrap gap-2">
                    {(r.related_ai_system_ids?.length ?? 0) > 0 ? (
                      <Link
                        href={aiSystemsFilterHref(r.related_ai_system_ids ?? [])}
                        className={`${CH_BTN_SECONDARY} px-3 py-1.5 text-xs`}
                      >
                        Betroffene Systeme anzeigen
                      </Link>
                    ) : null}
                    <Link
                      href="/board/eu-ai-act-readiness#governance-actions"
                      className={`${CH_BTN_SECONDARY} px-3 py-1.5 text-xs`}
                    >
                      Maßnahmen ansehen
                    </Link>
                    <Link
                      href="/tenant/eu-ai-act"
                      className={`${CH_BTN_PRIMARY} px-3 py-1.5 text-xs`}
                    >
                      Maßnahme erstellen
                    </Link>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="mb-8" aria-label="Vorgeschlagene Maßnahmen">
        <h2 className={`${CH_SECTION_LABEL} mb-4`}>
          Vorgeschlagene Maßnahmen (nicht persistiert)
        </h2>
        {data.suggested_actions.length === 0 ? (
          <p className="text-sm text-slate-500">
            Keine automatischen Vorschläge – oder alle Fokus-Systeme vollständig.
          </p>
        ) : (
          <ul className="space-y-3 text-sm text-slate-700">
            {data.suggested_actions.map((s, i) => (
              <li
                key={`${s.title}-${i}`}
                className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/60 px-4 py-3"
              >
                <span className="font-semibold text-slate-900">{s.title}</span>
                <span className="ml-2 text-xs text-slate-500">
                  {s.related_requirement} · Prio {s.suggested_priority}
                </span>
                <p className="mt-1 text-xs leading-relaxed text-slate-600">{s.rationale}</p>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section id="governance-actions" aria-label="Offene Maßnahmen">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <h2 className={CH_SECTION_LABEL}>Maßnahmen</h2>
          <div className="flex flex-wrap gap-2">
            <Link href="/tenant/eu-ai-act" className={`${CH_BTN_PRIMARY} px-4 py-2 text-sm`}>
              Neu
            </Link>
            <Link
              href="/tenant/eu-ai-act"
              className={`${CH_BTN_SECONDARY} px-4 py-2 text-sm`}
            >
              Im Tenant bearbeiten
            </Link>
          </div>
        </div>
        {data.open_governance_actions.length === 0 ? (
          <div
            className={`${CH_CARD} border-dashed border-slate-200 bg-slate-50/60 text-sm text-slate-600`}
            role="status"
          >
            Keine offenen Einträge in{" "}
            <code className="rounded bg-white px-1 text-xs ring-1 ring-slate-200">
              ai_governance_actions
            </code>
            . Über „Neu“ oder das Tenant-Cockpit können Sie Maßnahmen anlegen.
          </div>
        ) : (
          <div className={`${CH_CARD} overflow-hidden p-0`}>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/90 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    <th className="px-5 py-3">Titel</th>
                    <th className="px-5 py-3">Requirement</th>
                    <th className="px-5 py-3">Status</th>
                    <th className="px-5 py-3">Fällig</th>
                    <th className="px-5 py-3">Owner</th>
                    <th className="px-5 py-3 text-right">Aktion</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.open_governance_actions.map((a) => (
                    <tr key={a.id} className="transition hover:bg-slate-50/80">
                      <td className="px-5 py-4 font-semibold text-slate-900">{a.title}</td>
                      <td className="px-5 py-4 text-slate-600">{a.related_requirement}</td>
                      <td className="px-5 py-4">
                        <span className="inline-flex rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-800 ring-1 ring-slate-200/80">
                          {a.status}
                        </span>
                      </td>
                      <td className="px-5 py-4 tabular-nums text-slate-600">
                        {a.due_date
                          ? new Date(a.due_date).toLocaleDateString("de-DE")
                          : "–"}
                      </td>
                      <td className="px-5 py-4 text-slate-600">{a.owner ?? "–"}</td>
                      <td className="px-5 py-4 text-right">
                        <div className="flex flex-wrap justify-end gap-2">
                          {a.related_ai_system_id ? (
                            <Link
                              href={`/tenant/ai-systems/${encodeURIComponent(a.related_ai_system_id)}`}
                              className="text-xs font-semibold text-cyan-700 underline decoration-cyan-700/30 hover:text-cyan-900"
                            >
                              System
                            </Link>
                          ) : null}
                          <Link
                            href="/tenant/eu-ai-act"
                            className="text-xs font-semibold text-cyan-700 underline decoration-cyan-700/30 hover:text-cyan-900"
                          >
                            Bearbeiten
                          </Link>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
