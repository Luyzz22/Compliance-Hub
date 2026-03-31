"use client";

import Link from "next/link";
import React, { useMemo, useState } from "react";

import { CH_PAGE_NAV_LINK } from "@/lib/boardLayout";

export type AiSystemRegistryRow = {
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

type Props = {
  systems: AiSystemRegistryRow[];
  idFilterActive: boolean;
  totalBeforeClientFilter: number;
};

export function AiSystemsRegistryTableClient({
  systems,
  idFilterActive,
  totalBeforeClientFilter,
}: Props) {
  const [q, setQ] = useState("");
  const [bu, setBu] = useState("");
  const [risk, setRisk] = useState("");
  const [actCat, setActCat] = useState("");

  const businessUnits = useMemo(() => {
    const set = new Set(systems.map((s) => s.businessunit).filter(Boolean));
    return Array.from(set).sort();
  }, [systems]);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return systems.filter((s) => {
      if (needle) {
        const hay = `${s.name} ${s.id}`.toLowerCase();
        if (!hay.includes(needle)) return false;
      }
      if (bu && s.businessunit !== bu) return false;
      if (risk && s.risklevel !== risk) return false;
      if (actCat && s.aiactcategory !== actCat) return false;
      return true;
    });
  }, [systems, q, bu, risk, actCat]);

  return (
    <>
      <div className="flex flex-col gap-3 border-b border-[var(--sbs-border)] px-4 py-3 sm:flex-row sm:flex-wrap sm:items-end sm:gap-4 md:px-5">
        <label className="flex min-w-[12rem] flex-1 flex-col gap-1 text-xs font-medium text-slate-600">
          Suche (Name / ID)
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="z. B. Chatbot, sys-…"
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none ring-cyan-500/0 transition focus:border-cyan-300 focus:ring-2 focus:ring-cyan-500/20"
          />
        </label>
        <label className="flex min-w-[9rem] flex-col gap-1 text-xs font-medium text-slate-600">
          Business Unit
          <select
            value={bu}
            onChange={(e) => setBu(e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none focus:border-cyan-300 focus:ring-2 focus:ring-cyan-500/20"
          >
            <option value="">Alle</option>
            {businessUnits.map((b) => (
              <option key={b} value={b}>
                {b}
              </option>
            ))}
          </select>
        </label>
        <label className="flex min-w-[8rem] flex-col gap-1 text-xs font-medium text-slate-600">
          Risk Level
          <select
            value={risk}
            onChange={(e) => setRisk(e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none focus:border-cyan-300 focus:ring-2 focus:ring-cyan-500/20"
          >
            <option value="">Alle</option>
            <option value="high">high</option>
            <option value="limited">limited</option>
            <option value="low">low</option>
          </select>
        </label>
        <label className="flex min-w-[8rem] flex-col gap-1 text-xs font-medium text-slate-600">
          AI Act
          <input
            value={actCat}
            onChange={(e) => setActCat(e.target.value)}
            placeholder="Kategorie"
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none focus:border-cyan-300 focus:ring-2 focus:ring-cyan-500/20"
          />
        </label>
        <p className="text-xs text-[var(--sbs-text-secondary)] sm:ml-auto sm:pb-2">
          Anzeige: {filtered.length} von {systems.length}
          {idFilterActive ? ` (URL-Filter von ${totalBeforeClientFilter} gesamt)` : ""}
        </p>
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
              <th className="px-3 py-2 font-medium">Detail</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((s) => (
              <tr key={s.id}>
                <td>
                  <div className="font-semibold text-[var(--sbs-text-primary)]">{s.name}</div>
                  <div className="text-xs text-[var(--sbs-text-muted)]">{s.id}</div>
                </td>
                <td className="text-[var(--sbs-text-secondary)]">{s.businessunit}</td>
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
                <td className="text-xs text-[var(--sbs-text-secondary)]">{s.aiactcategory}</td>
                <td className="text-xs">
                  <span className="inline-flex rounded-full border border-[var(--sbs-border)] bg-slate-50 px-2 py-0.5 text-[var(--sbs-text-secondary)]">
                    {s.status}
                  </span>
                </td>
                <td className="text-xs text-[var(--sbs-text-secondary)]">{s.owneremail ?? "—"}</td>
                <td>
                  <Link
                    href={`/tenant/ai-systems/${encodeURIComponent(s.id)}`}
                    className={CH_PAGE_NAV_LINK + " text-xs no-underline hover:underline"}
                  >
                    Detail
                  </Link>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td
                  colSpan={7}
                  className="py-8 text-center text-sm text-[var(--sbs-text-secondary)]"
                >
                  Keine Einträge für die aktuellen Filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
