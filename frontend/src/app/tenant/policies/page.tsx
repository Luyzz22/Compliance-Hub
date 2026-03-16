import React from "react";

export default async function TenantPoliciesPage() {
  // Hier später: fetch aus /api/v1/policies & /api/v1/rules
  const policies: Record<string, unknown>[] = [];
  const rules: Record<string, unknown>[] = [];

  return (
    <>
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">
          Policy Engine
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          Mandantenfähige Policies & Regeln für AI‑Systeme (EU AI Act, NIS2,
          ISO‑Controls).
        </p>
      </header>

      <section className="mb-6 grid gap-4 md:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="text-xs font-medium text-slate-400">
            Policies gesamt
          </div>
          <div className="mt-2 text-3xl font-semibold">
            {policies.length}
          </div>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="text-xs font-medium text-slate-400">
            Regeln gesamt
          </div>
          <div className="mt-2 text-3xl font-semibold">
            {rules.length}
          </div>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="text-xs font-medium text-slate-400">
            Aktive Policies
          </div>
          <div className="mt-2 text-3xl font-semibold text-emerald-300">
            {policies.length}
          </div>
        </div>
      </section>

      <section className="rounded-xl border border-slate-800 bg-slate-900/60 mb-6">
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-3">
          <h2 className="text-sm font-semibold">Policies</h2>
          <button className="rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-200 hover:border-slate-500 hover:bg-slate-800">
            Neue Policy anlegen
          </button>
        </div>
        <div className="px-5 py-4 text-xs text-slate-500">
          Policy‑Liste wird angezeigt, sobald die Policy‑API angebunden ist.
        </div>
      </section>

      <section className="rounded-xl border border-slate-800 bg-slate-900/60">
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-3">
          <h2 className="text-sm font-semibold">Regeln</h2>
        </div>
        <div className="px-5 py-4 text-xs text-slate-500">
          Regel‑Definitionen (z.B. „High‑Risk erfordert DPIA“) folgen mit der
          Policy‑Engine‑Integration.
        </div>
      </section>
    </>
  );
}
