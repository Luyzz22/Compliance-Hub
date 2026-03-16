import React from "react";

export default async function TenantAuditLogPage() {
  // Später: fetch aus /api/v1/audit-events & /api/v1/audit-logs
  const events: Record<string, unknown>[] = [];

  return (
    <>
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">
          Audit & Evidence
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          Nachvollziehbare Audit‑Spur für AI‑Systeme, Policy‑Entscheidungen und
          Tenant‑Aktionen.
        </p>
      </header>

      <section className="rounded-xl border border-slate-800 bg-slate-900/60 mb-6">
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-3">
          <h2 className="text-sm font-semibold">Chronologischer Audit‑Log</h2>
          <button className="rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-200 hover:border-slate-500 hover:bg-slate-800">
            Export als CSV
          </button>
        </div>
        <div className="px-5 py-4 text-xs text-slate-500">
          {events.length === 0
            ? "Audit‑Einträge werden angezeigt, sobald die Audit‑APIs angebunden sind."
            : `${events.length} Einträge`}
        </div>
      </section>

      <section className="rounded-xl border border-slate-800 bg-slate-900/60">
        <div className="border-b border-slate-800 px-5 py-3">
          <h2 className="text-sm font-semibold">
            Evidence Bundles für Prüfungen
          </h2>
        </div>
        <div className="px-5 py-4 text-xs text-slate-500">
          Hier können später prüfbare Evidence‑Pakete (z.B. für NIS2 / ISO
          27001‑Audits) bereitgestellt werden.
        </div>
      </section>
    </>
  );
}
