import React from "react";

import { NIS2_RISKS } from "@/lib/marketing/demoData";

import { StatusChip } from "../ui/Primitives";

const LEVELS = [1, 2, 3, 4, 5] as const;

const IMPACT_LABEL: Record<number, string> = {
  1: "unwesentlich",
  2: "gering",
  3: "spürbar",
  4: "schwerwiegend",
  5: "existenzkritisch",
};

const LIKELIHOOD_LABEL: Record<number, string> = {
  1: "sehr selten",
  2: "selten",
  3: "möglich",
  4: "wahrscheinlich",
  5: "häufig",
};

type CellTone = "low" | "moderate" | "elevated" | "high";

function toneFor(impact: number, likelihood: number): CellTone {
  const score = impact * likelihood;
  if (score >= 15) return "high";
  if (score >= 9) return "elevated";
  if (score >= 4) return "moderate";
  return "low";
}

const CELL_CLASS: Record<CellTone, string> = {
  low: "bg-[var(--mk-ok-50)] border-[var(--mk-ok-100)]",
  moderate: "bg-[var(--mk-slate-100)] border-[var(--mk-slate-200)]",
  elevated: "bg-[var(--mk-warn-50)] border-[var(--mk-warn-100)]",
  high: "bg-[var(--mk-crit-50)] border-[var(--mk-crit-100)]",
};

const CELL_TEXT: Record<CellTone, string> = {
  low: "text-[var(--mk-ok-700)]",
  moderate: "text-[var(--mk-slate-600)]",
  elevated: "text-[var(--mk-warn-700)]",
  high: "text-[var(--mk-crit-700)]",
};

const LEGEND_SWATCH: Record<CellTone, string> = {
  low: "bg-[var(--mk-ok-500)]",
  moderate: "bg-[var(--mk-slate-400)]",
  elevated: "bg-[var(--mk-warn-500)]",
  high: "bg-[var(--mk-crit-500)]",
};

const TONE_LABEL: Record<CellTone, string> = {
  low: "gering",
  moderate: "mittel",
  elevated: "erhöht",
  high: "hoch / kritisch",
};

/**
 * Risiko-Heatmap nach Auswirkung × Eintrittswahrscheinlichkeit.
 * Jede Zelle nennt die Zahl der zugeordneten Risiken aus dem NIS2-Register.
 */
export function RiskHeatmap({ className = "" }: { className?: string }) {
  const counts = new Map<string, number>();
  for (const risk of NIS2_RISKS) {
    const key = `${risk.impact}:${risk.likelihood}`;
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }

  const topRisks = [...NIS2_RISKS]
    .sort((a, b) => b.impact * b.likelihood - a.impact * a.likelihood)
    .slice(0, 4);

  return (
    <div className={`mk-card overflow-hidden ${className}`.trim()}>
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--mk-bd)] bg-[var(--mk-panel-subtle)] px-4 py-2.5">
        <p className="mk-label">NIS2-Risikoregister · Art. 21</p>
        <p className="mk-mono text-[var(--mk-fg-faint)]">
          {NIS2_RISKS.length} bewertete Risiken
        </p>
      </div>

      <div className="p-4">
        <div className="mk-table-scroll">
          <table className="w-full min-w-[26rem] border-separate border-spacing-0">
            <caption className="sr-only">
              Risiko-Heatmap: Auswirkung nach Eintrittswahrscheinlichkeit, Anzahl der
              Risiken je Feld
            </caption>
            <thead>
              <tr>
                <th scope="col" className="w-24 p-1 text-left align-bottom">
                  <span className="mk-label">Auswirkung</span>
                </th>
                {LEVELS.map((likelihood) => (
                  <th key={likelihood} scope="col" className="p-1 align-bottom">
                    <span className="block text-[0.625rem] font-semibold text-[var(--mk-fg-faint)]">
                      {LIKELIHOOD_LABEL[likelihood]}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...LEVELS].reverse().map((impact) => (
                <tr key={impact}>
                  <th scope="row" className="p-1 text-left align-middle">
                    <span className="block text-[0.625rem] font-semibold text-[var(--mk-fg-faint)]">
                      {IMPACT_LABEL[impact]}
                    </span>
                  </th>
                  {LEVELS.map((likelihood) => {
                    const tone = toneFor(impact, likelihood);
                    const count = counts.get(`${impact}:${likelihood}`) ?? 0;
                    return (
                      <td key={likelihood} className="p-1">
                        <div
                          className={`flex h-11 items-center justify-center rounded-[6px] border ${CELL_CLASS[tone]}`}
                          title={`Auswirkung ${IMPACT_LABEL[impact]}, Eintritt ${LIKELIHOOD_LABEL[likelihood]}: ${count} Risiken`}
                        >
                          <span
                            className={`mk-num text-[0.8125rem] font-semibold ${
                              count ? CELL_TEXT[tone] : "text-[var(--mk-fg-faint)] opacity-45"
                            }`}
                          >
                            {count || "–"}
                          </span>
                        </div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2">
          <span className="mk-label">Eintrittswahrscheinlichkeit →</span>
          <ul className="flex flex-wrap gap-2">
            {(["low", "moderate", "elevated", "high"] as CellTone[]).map((tone) => (
              <li key={tone} className="flex items-center gap-1.5">
                <span
                  aria-hidden
                  className={`h-2.5 w-2.5 rounded-[3px] ${LEGEND_SWATCH[tone]}`}
                />
                <span className="text-[0.625rem] text-[var(--mk-fg-muted)]">
                  {TONE_LABEL[tone]}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="border-t border-[var(--mk-bd)] px-4 py-3.5">
        <p className="mk-label">Höchstbewertete Risiken</p>
        <ul className="mt-2 divide-y divide-[var(--mk-bd)]">
          {topRisks.map((risk) => (
            <li key={risk.id} className="flex items-center justify-between gap-3 py-2.5">
              <span className="min-w-0">
                <span className="flex items-center gap-2">
                  <span className="mk-mono text-[var(--mk-fg-faint)]">{risk.id}</span>
                  <span className="truncate text-[0.8125rem] font-medium text-[var(--mk-fg)]">
                    {risk.title}
                  </span>
                </span>
                <span className="mt-0.5 block text-[0.6875rem] text-[var(--mk-fg-faint)]">
                  NIS2 {risk.reference} · Owner {risk.owner} · {risk.treatment}
                </span>
              </span>
              <StatusChip
                tone={toneFor(risk.impact, risk.likelihood) === "high" ? "crit" : "warn"}
                dot={false}
              >
                {risk.impact * risk.likelihood}
              </StatusChip>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
