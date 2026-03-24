import React from "react";
import { fetchTenantAISystems } from "@/lib/api";

type AISystem = {
  id: string;
  name: string;
  businessunit: string;
  risklevel: string;
  aiactcategory: string;
  status: string;
  owneremail?: string;
};

function classNames(...values: (string | false | null | undefined)[]) {
  return values.filter(Boolean).join(" ");
}

type PageProps = {
  searchParams?: Promise<{ ids?: string }> | { ids?: string };
};

export default async function TenantAISystemsPage({ searchParams }: PageProps) {
  const systems = (await fetchTenantAISystems()) as AISystem[];

  const sp =
    searchParams !== undefined ? await Promise.resolve(searchParams) : {};
  const idFilterRaw = typeof sp.ids === "string" ? sp.ids : "";
  const idSet = new Set(
    idFilterRaw
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean),
  );
  const filtered =
    idSet.size > 0 ? systems.filter((s) => idSet.has(s.id)) : systems;

  const total = filtered.length;
  const active = filtered.filter((s) => s.status === "active").length;
  const highRisk = filtered.filter((s) => s.risklevel === "high").length;

  return (
    <>
      <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="sbs-h1">AI‑System Registry</h1>
          <p className="sbs-subtitle">
            Zentrale Übersicht aller registrierten AI‑Systeme dieses Tenants.
          </p>
        </div>
        <button type="button" className="sbs-btn-primary text-sm">
          Neues AI‑System anlegen
        </button>
      </header>

      {idSet.size > 0 ? (
        <div role="status" className="sbs-alert-warn mb-4 text-xs">
          Gefilterte Ansicht: {filtered.length} von {systems.length} Systemen
          (Deep-Link aus EU-AI-Act-Readiness).
        </div>
      ) : null}

      <section className="mb-6 grid gap-4 md:grid-cols-3">
        <div className="sbs-kpi-tile">
          <div className="sbs-kpi-label">AI‑Systeme gesamt</div>
          <div className="sbs-kpi-value">{total}</div>
        </div>
        <div className="sbs-kpi-tile">
          <div className="sbs-kpi-label">Aktive Systeme</div>
          <div className="sbs-kpi-value text-emerald-600">{active}</div>
        </div>
        <div className="sbs-kpi-tile">
          <div className="sbs-kpi-label">High‑Risk Systeme</div>
          <div className="sbs-kpi-value text-amber-600">{highRisk}</div>
        </div>
      </section>

      <section className="sbs-panel overflow-hidden p-0">
        <div className="flex items-center justify-between border-b border-[var(--sbs-border)] px-5 py-3">
          <h2 className="text-sm font-bold text-[var(--sbs-text-primary)]">
            AI‑Systeme
          </h2>
          <span className="text-xs text-[var(--sbs-text-secondary)]">
            {total} Einträge
            {idSet.size > 0 ? " (gefiltert)" : ""}
          </span>
        </div>
        <div className="sbs-table-wrap">
          <table className="sbs-table">
            <thead>
              <tr>
                <th className="px-5 py-2 font-medium">Name</th>
                <th className="px-3 py-2 font-medium">Business Unit</th>
                <th className="px-3 py-2 font-medium">Risk Level</th>
                <th className="px-3 py-2 font-medium">AI Act</th>
                <th className="px-3 py-2 font-medium">Status</th>
                <th className="px-3 py-2 font-medium">Owner</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s) => (
                <tr key={s.id}>
                  <td>
                    <div className="font-semibold text-[var(--sbs-text-primary)]">
                      {s.name}
                    </div>
                    <div className="text-xs text-[var(--sbs-text-muted)]">
                      {s.id}
                    </div>
                  </td>
                  <td className="text-[var(--sbs-text-secondary)]">
                    {s.businessunit}
                  </td>
                  <td>
                    <span
                      className={classNames(
                        "inline-flex rounded-full px-2 py-0.5 text-xs font-semibold",
                        s.risklevel === "high" &&
                          "border border-rose-200 bg-rose-50 text-rose-800",
                        s.risklevel === "limited" &&
                          "border border-amber-200 bg-amber-50 text-amber-900",
                        s.risklevel === "low" &&
                          "border border-emerald-200 bg-emerald-50 text-emerald-900",
                      )}
                    >
                      {s.risklevel}
                    </span>
                  </td>
                  <td className="text-xs text-[var(--sbs-text-secondary)]">
                    {s.aiactcategory}
                  </td>
                  <td className="text-xs">
                    <span className="inline-flex rounded-full border border-[var(--sbs-border)] bg-slate-50 px-2 py-0.5 text-[var(--sbs-text-secondary)]">
                      {s.status}
                    </span>
                  </td>
                  <td className="text-xs text-[var(--sbs-text-secondary)]">
                    {s.owneremail ?? "—"}
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="py-8 text-center text-sm text-[var(--sbs-text-secondary)]"
                  >
                    Noch keine AI‑Systeme erfasst.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
