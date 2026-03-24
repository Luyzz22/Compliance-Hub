import React from "react";

export default async function TenantPoliciesPage() {
  const policies: Record<string, unknown>[] = [];
  const rules: Record<string, unknown>[] = [];

  return (
    <>
      <header className="mb-8">
        <h1 className="sbs-h1">Policy Engine</h1>
        <p className="sbs-subtitle">
          Mandantenfähige Policies und Regeln für AI‑Systeme (EU AI Act, NIS2,
          ISO‑Controls).
        </p>
      </header>

      <section className="mb-6 grid gap-4 md:grid-cols-3">
        <div className="sbs-kpi-tile">
          <div className="sbs-kpi-label">Policies gesamt</div>
          <div className="sbs-kpi-value">{policies.length}</div>
        </div>
        <div className="sbs-kpi-tile">
          <div className="sbs-kpi-label">Regeln gesamt</div>
          <div className="sbs-kpi-value">{rules.length}</div>
        </div>
        <div className="sbs-kpi-tile">
          <div className="sbs-kpi-label">Aktive Policies</div>
          <div className="sbs-kpi-value text-emerald-600">{policies.length}</div>
        </div>
      </section>

      <section className="sbs-panel mb-6 overflow-hidden p-0">
        <div className="flex items-center justify-between border-b border-[var(--sbs-border)] px-5 py-3">
          <h2 className="text-sm font-bold text-[var(--sbs-text-primary)]">
            Policies
          </h2>
          <button type="button" className="sbs-btn-secondary text-xs py-2">
            Neue Policy anlegen
          </button>
        </div>
        <div className="px-5 py-4 text-xs text-[var(--sbs-text-secondary)]">
          Policy‑Liste wird angezeigt, sobald die Policy‑API angebunden ist.
        </div>
      </section>

      <section className="sbs-panel overflow-hidden p-0">
        <div className="border-b border-[var(--sbs-border)] px-5 py-3">
          <h2 className="text-sm font-bold text-[var(--sbs-text-primary)]">
            Regeln
          </h2>
        </div>
        <div className="px-5 py-4 text-xs text-[var(--sbs-text-secondary)]">
          Regel‑Definitionen (z. B. „High‑Risk erfordert DPIA“) folgen mit der
          Policy‑Engine‑Integration.
        </div>
      </section>
    </>
  );
}
