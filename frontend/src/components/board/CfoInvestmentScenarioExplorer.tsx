"use client";

import { useState } from "react";

import { HorizontalMetricBar } from "@/components/visualization/StrictCspMetrics";
import type {
  EnterpriseInvestmentInitiativeDto,
  InvestmentDecisionDto,
} from "@/lib/api";
import {
  CFO_SCENARIOS,
  getCfoScenario,
  rankInvestmentInitiatives,
  type CfoScenarioId,
} from "@/lib/cfoInvestmentScenario";

const DECISION_LABELS: Record<InvestmentDecisionDto, string> = {
  fund_now: "Jetzt finanzieren",
  sequence: "Sequenzieren",
  validate: "Validieren",
  hold: "Halten",
};

const DECISION_CLASSES: Record<InvestmentDecisionDto, string> = {
  fund_now: "border-emerald-300 bg-emerald-50 text-emerald-900",
  sequence: "border-cyan-300 bg-cyan-50 text-cyan-950",
  validate: "border-amber-300 bg-amber-50 text-amber-950",
  hold: "border-slate-300 bg-slate-100 text-slate-700",
};

type CfoInvestmentScenarioExplorerProps = {
  initiatives: EnterpriseInvestmentInitiativeDto[];
};

export function CfoInvestmentScenarioExplorer({
  initiatives,
}: CfoInvestmentScenarioExplorerProps) {
  const [scenarioId, setScenarioId] = useState<CfoScenarioId>("balanced");
  const scenario = getCfoScenario(scenarioId);
  const ranked = rankInvestmentInitiatives(initiatives, scenarioId);
  const lead = ranked[0];

  return (
    <section
      aria-labelledby="cfo-decision-lab-title"
      className="overflow-hidden rounded-[2rem] border border-slate-800 bg-slate-950 text-white shadow-xl shadow-slate-300/30"
    >
      <div className="border-b border-white/10 px-5 py-6 sm:px-7 lg:px-9 lg:py-8">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-300">
              CFO Decision Lab
            </p>
            <h2 id="cfo-decision-lab-title" className="mt-2 text-2xl font-semibold tracking-tight">
              Investitionsreihenfolge unter kontrollierten Annahmen
            </h2>
            <p className="mt-2 text-sm leading-6 text-slate-300">
              Szenarien gewichten vorhandene Governance-Signale neu. Sie verändern keine
              Quelldaten und lösen keine Budgetfreigabe aus.
            </p>
          </div>
          <div
            role="group"
            aria-label="Investitionsszenario auswählen"
            className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4"
          >
            {CFO_SCENARIOS.map((item) => {
              const selected = item.id === scenarioId;
              return (
                <button
                  key={item.id}
                  type="button"
                  aria-pressed={selected}
                  onClick={() => setScenarioId(item.id)}
                  className={`rounded-xl border px-3 py-2 text-left text-xs font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 ${
                    selected
                      ? "border-cyan-300 bg-cyan-300 text-slate-950"
                      : "border-white/15 bg-white/5 text-slate-200 hover:border-white/30 hover:bg-white/10"
                  }`}
                >
                  {item.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {lead ? (
        <div className="grid lg:grid-cols-[minmax(0,1.2fr)_minmax(20rem,0.8fr)]">
          <div className="border-b border-white/10 p-5 sm:p-7 lg:border-b-0 lg:border-r lg:p-9">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                  Szenario · {scenario.label}
                </p>
                <p className="mt-1 max-w-xl text-sm text-slate-300">{scenario.description}</p>
              </div>
              <span className="rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs text-slate-300">
                Relative Bewertung · keine Euro-Prognose
              </span>
            </div>

            <div className="mt-8 flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-sm text-slate-400">Priorität 01</p>
                <h3 className="mt-1 max-w-xl text-2xl font-semibold tracking-tight sm:text-3xl">
                  {lead.initiative_name_de}
                </h3>
                <span
                  className={`mt-4 inline-flex rounded-full border px-3 py-1 text-xs font-semibold ${DECISION_CLASSES[lead.scenario_decision]}`}
                >
                  {DECISION_LABELS[lead.scenario_decision]}
                </span>
              </div>
              <div className="shrink-0 text-left sm:text-right">
                <p className="text-5xl font-semibold tracking-tight text-white">
                  {lead.scenario_score}
                </p>
                <p className="text-xs uppercase tracking-[0.16em] text-slate-400">von 100</p>
              </div>
            </div>

            <dl className="mt-8 grid gap-5 sm:grid-cols-2">
              <FactorMetric
                label="Strategischer Wert"
                value={lead.strategic_value_score}
                weight={scenario.weights.strategicValue}
              />
              <FactorMetric
                label="Risikoreduktion"
                value={lead.risk_reduction_score}
                weight={scenario.weights.riskReduction}
              />
              <FactorMetric
                label="Ausführungssicherheit"
                value={lead.execution_confidence_score}
                weight={scenario.weights.executionConfidence}
              />
              <FactorMetric
                label="Kapitaleffizienz"
                value={lead.capital_efficiency_score}
                weight={scenario.weights.capitalEfficiency}
              />
            </dl>
          </div>

          <div className="bg-white/[0.03] p-5 sm:p-7 lg:p-9">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-sm font-semibold uppercase tracking-[0.14em] text-slate-300">
                Szenario-Rangfolge
              </h3>
              <span className="text-xs text-slate-500">{ranked.length} Initiativen</span>
            </div>
            <ol className="mt-5 space-y-3">
              {ranked.map((initiative) => (
                <li
                  key={initiative.initiative_id}
                  className="rounded-2xl border border-white/10 bg-white/5 p-4"
                >
                  <div className="flex items-start gap-3">
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10 text-xs font-semibold text-cyan-200">
                      {String(initiative.scenario_rank).padStart(2, "0")}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-semibold text-white">
                        {initiative.initiative_name_de}
                      </p>
                      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-400">
                        <span>{initiative.scenario_score}/100</span>
                        <span aria-hidden>·</span>
                        <span>{DECISION_LABELS[initiative.scenario_decision]}</span>
                        <span aria-hidden>·</span>
                        <span>Envelope {initiative.investment_envelope_band}</span>
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </div>
      ) : (
        <p role="status" className="px-7 py-10 text-sm text-slate-300">
          Noch keine investitionsfähigen Initiativen vorhanden.
        </p>
      )}
    </section>
  );
}

function FactorMetric({ label, value, weight }: { label: string; value: number; weight: number }) {
  return (
    <div>
      <div className="flex items-center justify-between gap-3 text-xs">
        <dt className="font-medium text-slate-300">{label}</dt>
        <dd className="text-slate-400">
          {value}/100 · Gewicht {weight}%
        </dd>
      </div>
      <HorizontalMetricBar
        value={value}
        label={`${label}: ${value} von 100`}
        className="mt-2 h-2 w-full"
        trackClassName="fill-slate-700"
        indicatorClassName="fill-cyan-300"
      />
    </div>
  );
}
