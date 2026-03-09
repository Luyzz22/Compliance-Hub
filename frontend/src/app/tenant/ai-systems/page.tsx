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

export default async function TenantAISystemsPage() {
  const systems = (await fetchTenantAISystems()) as AISystem[];

  const total = systems.length;
  const active = systems.filter((s) => s.status === "active").length;
  const highRisk = systems.filter((s) => s.risklevel === "high").length;

  return (
    <>
      <header className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            AI‑System Registry
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Zentrale Übersicht aller registrierten AI‑Systeme dieses Tenants.
          </p>
        </div>
        <button className="rounded-md border border-emerald-500/50 bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-300 hover:bg-emerald-500/20">
          Neues AI‑System anlegen
        </button>
      </header>

      <section className="mb-6 grid gap-4 md:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="text-xs font-medium text-slate-400">
            AI‑Systeme gesamt
          </div>
          <div className="mt-2 text-3xl font-semibold">{total}</div>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="text-xs font-medium text-slate-400">
            Aktive Systeme
          </div>
          <div className="mt-2 text-3xl font-semibold text-emerald-300">
            {active}
          </div>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="text-xs font-medium text-slate-400">
            High‑Risk Systeme
          </div>
          <div className="mt-2 text-3xl font-semibold text-amber-300">
            {highRisk}
          </div>
        </div>
      </section>

      <section className="rounded-xl border border-slate-800 bg-slate-900/60">
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-3">
          <h2 className="text-sm font-semibold">AI‑Systeme</h2>
          <span className="text-xs text-slate-500">{total} Einträge</span>
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
                <th className="px-3 py-2 font-medium">Owner</th>
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
                  <td className="px-3 py-2 text-xs text-slate-300">
                    {s.owneremail ?? "—"}
                  </td>
                </tr>
              ))}
              {systems.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-5 py-6 text-center text-xs text-slate-500"
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
