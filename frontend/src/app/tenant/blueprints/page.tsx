import React from "react";

export default async function TenantBlueprintsPage() {
  // Später: fetch aus Blueprint‑API (NIS2BASELINE_MIDMARKET, AIGOVERNANCE_STARTER etc.)
  const blueprints: { id: string; title: string; description: string }[] = [
    {
      id: "NIS2_BASELINE_MIDMARKET",
      title: "NIS2-Baseline für Mittelstand",
      description:
        "Basis-Set an Controls für NIS2 / ISO 27001 im DACH-Mittelstand.",
    },
    {
      id: "AI_GOVERNANCE_STARTER",
      title: "AI Governance Starter",
      description:
        "High-Level AI-Governance für EU AI Act / ISO 42001 im Mittelstand.",
    },
  ];

  return (
    <>
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">
          Compliance Blueprints
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          Kuratierte Blueprint‑Sets für NIS2, EU AI Act und ISO‑Standards.
        </p>
      </header>

      <section className="grid gap-4 md:grid-cols-2">
        {blueprints.map((bp) => (
          <div
            key={bp.id}
            className="rounded-xl border border-slate-800 bg-slate-900/60 p-5"
          >
            <div className="text-xs font-mono uppercase text-slate-500">
              {bp.id}
            </div>
            <h2 className="mt-1 text-sm font-semibold">{bp.title}</h2>
            <p className="mt-2 text-xs text-slate-400">{bp.description}</p>
            <button className="mt-4 rounded-md border border-emerald-500/40 bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-300 hover:bg-emerald-500/20">
              Blueprint aktivieren
            </button>
          </div>
        ))}
      </section>
    </>
  );
}
