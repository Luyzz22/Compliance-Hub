import React from "react";

export default async function TenantBlueprintsPage() {
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
        <h1 className="sbs-h1">Compliance Blueprints</h1>
        <p className="sbs-subtitle">
          Kuratierte Blueprint‑Sets für NIS2, EU AI Act und ISO‑Standards.
        </p>
      </header>

      <section className="grid gap-4 md:grid-cols-2">
        {blueprints.map((bp) => (
          <div key={bp.id} className="sbs-panel p-5">
            <div className="font-mono text-xs uppercase text-[var(--sbs-text-muted)]">
              {bp.id}
            </div>
            <h2 className="mt-1 text-sm font-bold text-[var(--sbs-text-primary)]">
              {bp.title}
            </h2>
            <p className="mt-2 text-xs text-[var(--sbs-text-secondary)]">
              {bp.description}
            </p>
            <button
              type="button"
              className="mt-4 rounded-lg border border-emerald-600/40 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-900 hover:bg-emerald-100"
            >
              Blueprint aktivieren
            </button>
          </div>
        ))}
      </section>
    </>
  );
}
