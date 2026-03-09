import React from "react";
import {
  fetchTenantAISystems,
  fetchTenantViolations,
} from "@/lib/api";

type AISystem = {
  id: string;
  name: string;
  businessunit: string;
  risklevel: string;
  aiactcategory: string;
  status: string;
};

type Violation = {
  id: string;
  aisystemid: string;
  ruleid: string;
  message: string;
  createdat: string;
};

function classNames(...values: (string | false | null | undefined)[]) {
  return values.filter(Boolean).join(" ");
}

export default async function TenantComplianceOverviewPage() {
  const [systems, violations] = (await Promise.all([
    fetchTenantAISystems(),
    fetchTenantViolations(),
  ])) as [AISystem[], Violation[]];

  const totalSystems = systems.length;
  const highRisk = systems.filter((s) => s.risklevel === "high").length;
  const openViolations = violations.length;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 flex">
      {/* Sidebar */}
      <aside className="w-64 border-r border-slate-800 bg-slate-950/80 backdrop-blur">
        <div className="px-6 py-5 border-b border-slate-800">
          <div className="text-xs font-semibold tracking-widest text-slate-400">
            COMPLIANCE HUB
          </div>
          <div className="mt-1 text-sm text-slate-300">
            Tenant: <span className="font-medium">tenant-overview-001</span>
          </div>
        </div>
        <nav className="px-3 py-4 space-y-1 text-sm">
          <div className="px-2 pb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Overview
          </div>
          <a
            className="flex items-center gap-2 rounded-md px-2 py-1.5 bg-slate-800 text-slate-50"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            Tenant Compliance
          </a>
          <a className="flex items-center gap-2 rounded-md px-2 py-1.5 text-slate-400 hover:bg-slate-900 hover:text-slate-50">
            AI Systems
          </a>
          <a className="flex items-center gap-2 rounded-md px-2 py-1.5 text-slate-400 hover:bg-slate-900 hover:text-slate-50">
            Policies & Rules
          </a>
          <a className="flex items-center gap-2 rounded-md px-2 py-1.5 text-slate-400 hover:bg-slate-900 hover:text-slate-50">
            Audit Log
          </a>
        </nav>
      </aside>

      {/* Main */}
      <main className="flex-1 p-8">
        {/* Header */}
        <header className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Tenant Compliance Overview
            </h1>
            <p className="mt-1 text-sm text-slate-400">
              Konsolidierter Überblick über AI‑Systeme, Risiken und Violations
              für diesen Tenant.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-2 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-300">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              Platform Status: OK
            </span>
            <button className="rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-200 hover:border-slate-500 hover:bg-slate-800">
              Export Report
            </button>
          </div>
        </header>

        {/* KPI Cards */}
        <section className="mb-8 grid gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="text-xs font-medium text-slate-400">
              AI‑Systeme gesamt
            </div>
            <div className="mt-2 text-3xl font-semibold">{totalSystems}</div>
            <div className="mt-2 text-xs text-slate-500">
              Registrierte produktive und in Prüfung befindliche Systeme.
            </div>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="text-xs font-medium text-slate-400">
              High‑Risk Systeme
            </div>
            <div className="mt-2 text-3xl font-semibold text-amber-300">
              {highRisk}
            </div>
            <div className="mt-2 text-xs text-slate-500">
              Basierend auf AI‑Act Kategorie & Risikoeinstufung.
            </div>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="text-xs font-medium text-slate-400">
              Offene Policy‑Violations
            </div>
            <div className="mt-2 text-3xl font-semibold text-rose-300">
              {openViolations}
            </div>
            <div className="mt-2 text-xs text-slate-500">
              Aggregiert über alle AI‑Systeme dieses Tenants.
            </div>
          </div>
        </section>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* AI Systems Table */}
          <section className="lg:col-span-2 rounded-xl border border-slate-800 bg-slate-900/60">
            <div className="flex items-center justify-between border-b border-slate-800 px-5 py-3">
              <h2 className="text-sm font-semibold">AI‑Systeme</h2>
              <span className="text-xs text-slate-500">
                {totalSystems} Einträge
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-900/80 text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-5 py-2 font-medium">Name</th>
                    <th className="px-3 py-2 font-medium">Business Unit</th>
                    <th className="px-3 py-2 font-medium">Risk Level</th>
                    <th className="px-3 py-2 font-medium">AI Act</th>
                    <th className="px-3 py-2 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {systems.map((s) => (
                    <tr
                      key={s.id}
                      className="border-t border-slate-800/80 hover:bg-slate-900"
                    >
                      <td className="px-5 py-2 text-slate-50">
                        <div className="font-medium">{s.name}</div>
                        <div className="text-xs text-slate-500">{s.id}</div>
                      </td>
                      <td className="px-3 py-2 text-slate-300">
                        {s.businessunit}
                      </td>
                      <td className="px-3 py-2">
                        <span
                          className={classNames(
                            "inline-flex rounded-full px-2 py-0.5 text-xs font-medium",
                            s.risklevel === "high" &&
                              "bg-rose-500/10 text-rose-300 border border-rose-500/40",
                            s.risklevel === "limited" &&
                              "bg-amber-500/10 text-amber-300 border border-amber-500/40",
                            s.risklevel === "low" &&
                              "bg-emerald-500/10 text-emerald-300 border border-emerald-500/40"
                          )}
                        >
                          {s.risklevel}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-xs text-slate-300">
                        {s.aiactcategory}
                      </td>
                      <td className="px-3 py-2 text-xs">
                        <span className="inline-flex rounded-full border border-slate-700 px-2 py-0.5 text-slate-300">
                          {s.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {systems.length === 0 && (
                    <tr>
                      <td
                        colSpan={5}
                        className="px-5 py-6 text-center text-xs text-slate-500"
                      >
                        Noch keine AI‑Systeme für diesen Tenant erfasst.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>

          {/* Violations List */}
          <section className="rounded-xl border border-slate-800 bg-slate-900/60">
            <div className="flex items-center justify-between border-b border-slate-800 px-5 py-3">
              <h2 className="text-sm font-semibold">Aktuelle Violations</h2>
              <span className="text-xs text-slate-500">
                {openViolations} offen
              </span>
            </div>
            <div className="max-h-80 space-y-3 overflow-y-auto px-5 py-4 text-xs">
              {violations.map((v) => (
                <div
                  key={v.id}
                  className="rounded-lg border border-rose-500/30 bg-rose-500/5 p-3"
                >
                  <div className="mb-1 text-rose-200">
                    {v.message}
                  </div>
                  <div className="flex justify-between text-[11px] text-rose-300/80">
                    <span>System: {v.aisystemid}</span>
                    <span>Rule: {v.ruleid}</span>
                  </div>
                  <div className="mt-1 text-[11px] text-rose-200/70">
                    {new Date(v.createdat).toLocaleString()}
                  </div>
                </div>
              ))}
              {violations.length === 0 && (
                <div className="text-center text-slate-500">
                  Aktuell keine offenen Violations.
                </div>
              )}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
