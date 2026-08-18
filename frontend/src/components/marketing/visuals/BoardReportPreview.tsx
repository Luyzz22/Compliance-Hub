import React from "react";

import {
  ACTION_PLAN,
  BOARD_DECISIONS,
  BOARD_KPIS,
  DEADLINES,
  DEMO_ORG,
  FRAMEWORK_COVERAGE,
} from "@/lib/marketing/demoData";

import { IconAlert, IconClock } from "../ui/Icons";
import { Meter, StatusChip, toneForCoverage } from "../ui/Primitives";

function Headline({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[0.625rem] font-semibold uppercase tracking-[0.12em] text-[#74869e]">
      {children}
    </p>
  );
}

/**
 * Board-Report-Ansicht: Lage, Entscheidungsbedarf, Fristen.
 * Ziel ist, dass eine Geschäftsführung in Sekunden erkennt, was zu tun ist.
 */
export function BoardReportPreview({ className = "" }: { className?: string }) {
  const dueSoon = ACTION_PLAN.filter((action) => action.priority === "kritisch");

  return (
    <div
      className={`mk-dark overflow-hidden rounded-[16px] border border-white/10 bg-[#0b1727] shadow-[var(--mk-shadow-dark)] ${className}`.trim()}
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 bg-white/[0.03] px-4 py-3">
        <div>
          <Headline>Board Report · {DEMO_ORG.reportingPeriod}</Headline>
          <p className="mt-1 text-[0.9375rem] font-semibold text-white">{DEMO_ORG.name}</p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <StatusChip tone="crit">{BOARD_KPIS.openDecisions} Entscheidungen erforderlich</StatusChip>
          <StatusChip tone="neutral">{DEMO_ORG.asOf}</StatusChip>
        </div>
      </div>

      <div className="grid gap-4 p-4 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
        {/* Lage */}
        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
            {[
              { label: "Readiness", value: `${BOARD_KPIS.readinessScore}%` },
              { label: "High-Risk", value: `${BOARD_KPIS.aiSystemsHighRisk}` },
              { label: "Evidence", value: `${BOARD_KPIS.evidenceCoverage}%` },
              { label: "NIS2 High+", value: `${BOARD_KPIS.nis2HighRisks}` },
            ].map((kpi) => (
              <div
                key={kpi.label}
                className="rounded-[10px] border border-white/10 bg-white/[0.04] px-3 py-2.5"
              >
                <p className="truncate text-[0.5625rem] font-semibold uppercase tracking-[0.1em] text-[#74869e]">
                  {kpi.label}
                </p>
                <p className="mk-num mt-1.5 text-[1.25rem] font-semibold leading-none text-white">
                  {kpi.value}
                </p>
              </div>
            ))}
          </div>

          <div className="rounded-[10px] border border-white/10 bg-white/[0.04] p-3.5">
            <Headline>Framework Coverage</Headline>
            <ul className="mt-2.5 space-y-2">
              {FRAMEWORK_COVERAGE.map((framework) => (
                <li key={framework.id} className="grid grid-cols-[7.5rem_minmax(0,1fr)_2.5rem] items-center gap-2.5">
                  <span className="truncate text-[0.6875rem] text-[#c3cede]">
                    {framework.label}
                  </span>
                  <Meter
                    value={framework.coverage}
                    tone={toneForCoverage(framework.coverage)}
                    label={framework.label}
                    height={5}
                  />
                  <span className="mk-num text-right text-[0.6875rem] font-semibold text-white">
                    {framework.coverage}%
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-[10px] border border-white/10 bg-white/[0.04] p-3.5">
            <Headline>Nächste Review-Termine</Headline>
            <ul className="mt-2 divide-y divide-white/10">
              {DEADLINES.map((deadline) => (
                <li key={deadline.label} className="flex items-center justify-between gap-3 py-2">
                  <span className="min-w-0">
                    <span className="block text-[0.75rem] font-medium text-white">
                      {deadline.label}
                    </span>
                    <span className="block truncate text-[0.625rem] text-[#8798b0]">
                      {deadline.detail}
                    </span>
                  </span>
                  <span className="flex shrink-0 items-center gap-1.5 text-[0.6875rem] text-[#c3cede]">
                    <IconClock className="h-3.5 w-3.5 text-[#74869e]" />
                    <span className="mk-num">in {deadline.inDays} Tagen</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Entscheidungsbedarf */}
        <div className="flex flex-col gap-3">
          <div className="rounded-[10px] border border-[rgba(217,45,32,0.36)] bg-[rgba(217,45,32,0.1)] p-3.5">
            <div className="flex items-center gap-2">
              <IconAlert className="h-4 w-4 shrink-0 text-[#fda29b]" />
              <Headline>Entscheidungen des Gremiums</Headline>
            </div>
            <ol className="mt-2.5 space-y-2.5">
              {BOARD_DECISIONS.map((decision, index) => (
                <li key={decision.title} className="grid grid-cols-[1.25rem_minmax(0,1fr)] gap-2">
                  <span className="mk-num text-[0.6875rem] font-bold text-[#fda29b]">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <span className="min-w-0">
                    <span className="block text-[0.75rem] font-semibold text-white">
                      {decision.title}
                    </span>
                    <span className="mt-0.5 block text-[0.6875rem] leading-relaxed text-[#c3cede]">
                      {decision.context}
                    </span>
                    <span className="mt-1 block text-[0.6875rem] leading-relaxed text-[#8798b0]">
                      Benötigt: {decision.needed}
                    </span>
                  </span>
                </li>
              ))}
            </ol>
          </div>

          <div className="min-w-0 overflow-hidden rounded-[10px] border border-white/10 bg-white/[0.04]">
            <div className="flex items-center justify-between gap-2 border-b border-white/10 px-3.5 py-2.5">
              <Headline>Kritische offene Maßnahmen</Headline>
              <span className="mk-num text-[0.625rem] text-[#74869e]">
                {BOARD_KPIS.actionsDueBySeptember} bis 30.09. fällig
              </span>
            </div>
            <ul className="divide-y divide-white/10">
              {dueSoon.map((action) => (
                <li key={action.id} className="px-3.5 py-2.5">
                  <div className="flex items-start justify-between gap-3">
                    <p className="min-w-0 text-[0.75rem] font-medium leading-snug text-white">
                      {action.title}
                    </p>
                    <p className="mk-num shrink-0 text-[0.6875rem] text-[#d3dcea]">
                      {action.due}
                    </p>
                  </div>
                  <p className="mk-mono mt-1 truncate text-[#74869e]">
                    {action.framework} {action.reference} · {action.owner} ·{" "}
                    {action.ownerRole}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      <p className="border-t border-white/10 bg-white/[0.02] px-4 py-2.5 text-[0.6875rem] leading-relaxed text-[#74869e]">
        Der Bericht bereitet den Stand für die Entscheidung auf. Die Bewertung und Freigabe
        bleibt bei den verantwortlichen Personen.
      </p>
    </div>
  );
}
