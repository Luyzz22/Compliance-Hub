"use client";

import React, { useMemo, useState } from "react";

import { CH_CARD, CH_SECTION_LABEL } from "@/lib/boardLayout";

export type AuditLogDemoRow = {
  id: string;
  ts: string;
  actor: string;
  entityType: string;
  action: string;
  tenant: string;
  detail?: string;
};

type Props = {
  tenantId: string;
  rows: AuditLogDemoRow[];
};

export function TenantAuditLogTableClient({ tenantId, rows }: Props) {
  const [entity, setEntity] = useState("");
  const [action, setAction] = useState("");
  const [windowKey, setWindowKey] = useState<"7" | "30" | "all">("all");
  const [asOfMs, setAsOfMs] = useState(() => Date.now());

  const entityTypes = useMemo(() => {
    const s = new Set(rows.map((r) => r.entityType));
    return Array.from(s).sort();
  }, [rows]);
  const actions = useMemo(() => {
    const s = new Set(rows.map((r) => r.action));
    return Array.from(s).sort();
  }, [rows]);

  const filtered = useMemo(() => {
    const now = asOfMs;
    const maxAge =
      windowKey === "all" ? null : windowKey === "7" ? 7 * 86_400_000 : 30 * 86_400_000;
    return rows.filter((r) => {
      if (entity && r.entityType !== entity) return false;
      if (action && r.action !== action) return false;
      if (maxAge != null) {
        const t = new Date(r.ts).getTime();
        if (Number.isFinite(t) && now - t > maxAge) return false;
      }
      return true;
    });
  }, [asOfMs, action, entity, rows, windowKey]);

  return (
    <div className={`${CH_CARD} overflow-hidden p-0`}>
      <div className="flex flex-col gap-3 border-b border-slate-200/80 px-5 py-4 sm:flex-row sm:flex-wrap sm:items-end">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">Audit-Log</h2>
          <p className="mt-1 text-xs text-slate-500">
            Demonstrationsdaten bis die Audit-API angebunden ist. Mandant:{" "}
            <span className="font-mono font-medium text-slate-700">{tenantId}</span>
          </p>
        </div>
        <div className="flex flex-wrap gap-2 sm:ml-auto">
          <label className="flex flex-col gap-1 text-[0.65rem] font-semibold uppercase tracking-wide text-slate-500">
            Zeitraum
            <select
              value={windowKey}
              onChange={(e) => {
                setWindowKey(e.target.value as "7" | "30" | "all");
                setAsOfMs(Date.now());
              }}
              className="rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-900"
            >
              <option value="all">Alle</option>
              <option value="30">30 Tage</option>
              <option value="7">7 Tage</option>
            </select>
          </label>
          <label className="flex flex-col gap-1 text-[0.65rem] font-semibold uppercase tracking-wide text-slate-500">
            Entity
            <select
              value={entity}
              onChange={(e) => setEntity(e.target.value)}
              className="rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-900"
            >
              <option value="">Alle</option>
              {entityTypes.map((e) => (
                <option key={e} value={e}>
                  {e}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-[0.65rem] font-semibold uppercase tracking-wide text-slate-500">
            Aktion
            <select
              value={action}
              onChange={(e) => setAction(e.target.value)}
              className="rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-900"
            >
              <option value="">Alle</option>
              {actions.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>
      <p className="border-b border-slate-100 px-5 py-2 text-xs text-slate-500">
        <span className={CH_SECTION_LABEL + " mr-2"}>Treffer</span>
        {filtered.length} von {rows.length}
      </p>
      <div className="sbs-table-wrap">
        <table className="sbs-table">
          <thead>
            <tr>
              <th className="px-4 py-2 text-left text-xs font-semibold text-slate-600">
                Zeitstempel
              </th>
              <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600">Akteur</th>
              <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600">
                Entity-Typ
              </th>
              <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600">Aktion</th>
              <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600">Mandant</th>
              <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600">Detail</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((r) => (
              <tr key={r.id}>
                <td className="whitespace-nowrap text-xs text-slate-800">
                  {new Date(r.ts).toLocaleString("de-DE")}
                </td>
                <td className="max-w-[10rem] truncate text-xs text-slate-700">{r.actor}</td>
                <td className="text-xs font-medium text-slate-800">{r.entityType}</td>
                <td className="text-xs text-slate-700">{r.action}</td>
                <td className="font-mono text-[0.7rem] text-slate-600">{r.tenant}</td>
                <td className="max-w-xs truncate text-xs text-slate-500">{r.detail ?? "—"}</td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="py-10 text-center text-sm text-slate-500">
                  Keine Einträge für die gewählten Filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
