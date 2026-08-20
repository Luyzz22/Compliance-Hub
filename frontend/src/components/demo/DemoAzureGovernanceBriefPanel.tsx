"use client";

import { useId, useState } from "react";
import type { KeyboardEvent } from "react";

import {
  postDemoAzureGovernanceBrief,
  type DemoAzureBriefDto,
  type DemoAzureBriefScenario,
} from "@/lib/api";
import { CH_BTN_PRIMARY, CH_CARD, CH_SECTION_LABEL } from "@/lib/boardLayout";

const SCENARIOS: ReadonlyArray<{
  id: DemoAzureBriefScenario;
  label: string;
  description: string;
}> = [
  {
    id: "governance_release_gate",
    label: "Release Gate",
    description: "Evidence, Zuständigkeit und Vier-Augen-Freigabe",
  },
  {
    id: "supplier_risk",
    label: "Lieferantenrisiko",
    description: "Ausstieg, Unterauftragnehmer und Änderungskontrolle",
  },
  {
    id: "incident_readiness",
    label: "Incident Readiness",
    description: "Eskalation, Beweissicherung und Wiederanlauf",
  },
];

export function DemoAzureGovernanceBriefPanel({ tenantId }: { tenantId: string }) {
  const headingId = useId();
  const [scenario, setScenario] = useState<DemoAzureBriefScenario>(
    "governance_release_gate",
  );
  const [result, setResult] = useState<DemoAzureBriefDto | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function generateBrief() {
    setError(null);
    setResult(null);
    setIsLoading(true);
    try {
      setResult(await postDemoAzureGovernanceBrief(tenantId, scenario));
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Das synthetische Briefing konnte nicht erzeugt werden.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  function selectScenarioFromKeyboard(
    event: KeyboardEvent<HTMLButtonElement>,
    nextScenario: DemoAzureBriefScenario,
  ) {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    setScenario(nextScenario);
  }

  return (
    <section className={`${CH_CARD} overflow-hidden p-0`} aria-labelledby={headingId}>
      <div className="border-b border-slate-200 bg-slate-950 px-5 py-6 text-white sm:px-7">
        <div className="flex flex-wrap items-center gap-2 text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-cyan-200">
          <span>Azure OpenAI</span>
          <span aria-hidden="true" className="text-slate-500">
            /
          </span>
          <span>Kontrollierter Demopfad</span>
        </div>
        <div className="mt-3 grid gap-5 lg:grid-cols-[minmax(0,1fr)_18rem] lg:items-end">
          <div>
            <h2 id={headingId} className="text-balance text-2xl font-semibold tracking-tight">
              Vom synthetischen Sachverhalt zum prüfbaren Executive Briefing
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">
              Wählen Sie ein fest definiertes Szenario. Es werden weder Freitext noch Dokumente
              oder Kundendaten übertragen. Azure liefert einen Entwurf; die Entscheidung bleibt
              immer beim Menschen.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-white/15 bg-white/15 text-xs">
            <div className="bg-slate-950/80 px-3 py-3">
              <p className="text-slate-400">Datenklasse</p>
              <p className="mt-1 font-semibold text-white">Public / synthetisch</p>
            </div>
            <div className="bg-slate-950/80 px-3 py-3">
              <p className="text-slate-400">Entscheidung</p>
              <p className="mt-1 font-semibold text-white">Human Review</p>
            </div>
          </div>
        </div>
      </div>

      <div className="px-5 py-6 sm:px-7">
        <p className={CH_SECTION_LABEL}>Synthetisches Szenario wählen</p>
        <div className="mt-3 grid gap-3 md:grid-cols-3" role="group" aria-label="Szenario">
          {SCENARIOS.map((item, index) => {
            const selected = item.id === scenario;
            return (
              <button
                key={item.id}
                type="button"
                aria-pressed={selected}
                onClick={() => setScenario(item.id)}
                onKeyDown={(event) => selectScenarioFromKeyboard(event, item.id)}
                className={`min-h-24 rounded-xl border px-4 py-3 text-left outline-none transition focus-visible:ring-2 focus-visible:ring-cyan-700 focus-visible:ring-offset-2 ${
                  selected
                    ? "border-cyan-700 bg-cyan-50 text-slate-950"
                    : "border-slate-200 bg-white text-slate-700 hover:border-slate-400"
                }`}
              >
                <span className="block text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-slate-500">
                  0{index + 1}
                </span>
                <span className="mt-1 block text-sm font-semibold">{item.label}</span>
                <span className="mt-1 block text-xs leading-5 text-slate-600">
                  {item.description}
                </span>
              </button>
            );
          })}
        </div>

        <ol
          className="mt-6 grid overflow-hidden rounded-xl border border-slate-200 bg-slate-50 text-xs text-slate-600 sm:grid-cols-4"
          aria-label="Verarbeitungsschritte"
        >
          {["Fester Sachverhalt", "Guardrails", "Azure EU Data Zone", "Human Review"].map(
            (step, index) => (
              <li
                key={step}
                className="flex min-h-12 items-center gap-2 border-b border-slate-200 px-3 last:border-b-0 sm:border-b-0 sm:border-r sm:last:border-r-0"
              >
                <span className="font-mono text-cyan-800">{index + 1}</span>
                <span>{step}</span>
              </li>
            ),
          )}
        </ol>

        <div className="mt-5 flex flex-wrap items-center gap-3">
          <button
            type="button"
            className={`${CH_BTN_PRIMARY} min-h-11 text-sm disabled:cursor-wait disabled:opacity-60`}
            disabled={isLoading}
            onClick={() => void generateBrief()}
          >
            {isLoading ? "Azure verarbeitet das Szenario…" : "Executive Briefing erzeugen"}
          </button>
          <p className="max-w-xl text-xs leading-5 text-slate-500">
            Server-seitige Tages- und Tokenlimits begrenzen den Demobetrieb. Keine
            Rechtsberatung und keine automatische Rechts- oder Freigabeentscheidung.
          </p>
        </div>

        <div aria-live="polite" aria-atomic="true">
          {error ? (
            <p role="alert" className="mt-5 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900">
              {error}
            </p>
          ) : null}

          {result ? (
            <article className="mt-6 border-t border-slate-200 pt-6" aria-label="Azure Briefing">
              <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_17rem]">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700">
                    Azure-Antwort erhalten · Fachprüfung offen
                  </p>
                  <h3 className="mt-2 text-xl font-semibold tracking-tight text-slate-950">
                    {result.title}
                  </h3>
                  <p className="mt-3 text-sm leading-6 text-slate-700">
                    {result.executive_summary}
                  </p>
                  <h4 className="mt-5 text-sm font-semibold text-slate-950">
                    Empfohlene nächste Prüfhandlungen
                  </h4>
                  <ol className="mt-3 space-y-2">
                    {result.recommended_actions.map((action, index) => (
                      <li
                        key={`${index}-${action}`}
                        className="flex gap-3 text-sm leading-6 text-slate-700"
                      >
                        <span className="font-mono text-cyan-800">0{index + 1}</span>
                        <span>{action}</span>
                      </li>
                    ))}
                  </ol>
                  <p className="mt-5 border-l-2 border-amber-400 pl-4 text-sm leading-6 text-slate-700">
                    <strong>Human Review:</strong> {result.human_review_note}
                  </p>
                </div>

                <dl className="h-fit divide-y divide-slate-200 rounded-xl border border-slate-200 bg-slate-50 px-4 text-xs">
                  <div className="py-3">
                    <dt className="text-slate-500">Provider</dt>
                    <dd className="mt-1 font-semibold text-slate-900">Azure OpenAI</dd>
                  </div>
                  <div className="py-3">
                    <dt className="text-slate-500">Deployment</dt>
                    <dd className="mt-1 break-all font-mono text-slate-900">{result.model_id}</dd>
                  </div>
                  <div className="py-3">
                    <dt className="text-slate-500">Token (geschätzt)</dt>
                    <dd className="mt-1 font-mono text-slate-900">
                      {result.input_tokens_est} in / {result.output_tokens_est} out
                    </dd>
                  </div>
                  <div className="py-3">
                    <dt className="text-slate-500">Datenvertrag</dt>
                    <dd className="mt-1 font-semibold text-slate-900">
                      {result.synthetic_data_only ? "Synthetisch bestätigt" : "Nicht bestätigt"}
                    </dd>
                  </div>
                </dl>
              </div>
            </article>
          ) : null}
        </div>
      </div>
    </section>
  );
}
