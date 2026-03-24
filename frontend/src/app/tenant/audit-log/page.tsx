import React from "react";

export default async function TenantAuditLogPage() {
  const events: Record<string, unknown>[] = [];

  return (
    <>
      <header className="mb-8">
        <h1 className="sbs-h1">Audit &amp; Evidence</h1>
        <p className="sbs-subtitle">
          Nachvollziehbare Audit‑Spur für AI‑Systeme, Policy‑Entscheidungen und
          Tenant‑Aktionen.
        </p>
      </header>

      <section className="sbs-panel mb-6 overflow-hidden p-0">
        <div className="flex items-center justify-between border-b border-[var(--sbs-border)] px-5 py-3">
          <h2 className="text-sm font-bold text-[var(--sbs-text-primary)]">
            Chronologischer Audit‑Log
          </h2>
          <button type="button" className="sbs-btn-secondary text-xs py-2">
            Export als CSV
          </button>
        </div>
        <div className="px-5 py-4 text-xs text-[var(--sbs-text-secondary)]">
          {events.length === 0
            ? "Audit‑Einträge werden angezeigt, sobald die Audit‑APIs angebunden sind."
            : `${events.length} Einträge`}
        </div>
      </section>

      <section className="sbs-panel overflow-hidden p-0">
        <div className="border-b border-[var(--sbs-border)] px-5 py-3">
          <h2 className="text-sm font-bold text-[var(--sbs-text-primary)]">
            Evidence Bundles für Prüfungen
          </h2>
        </div>
        <div className="px-5 py-4 text-xs text-[var(--sbs-text-secondary)]">
          Hier können später prüfbare Evidence‑Pakete (z. B. für NIS2 / ISO
          27001‑Audits) bereitgestellt werden.
        </div>
      </section>
    </>
  );
}
