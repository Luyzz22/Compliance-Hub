"use client";

import React, { useCallback, useState } from "react";
import {
  createBoardReportAuditRecord,
  fetchBoardReportAuditRecords,
  type BoardReportAuditRecord,
} from "@/lib/api";

const LIST_LIMIT = 5;

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("de-DE", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function BoardReportAuditSection() {
  const [records, setRecords] = useState<BoardReportAuditRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdId, setCreatedId] = useState<string | null>(null);

  const loadRecords = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await fetchBoardReportAuditRecords({
        limit: LIST_LIMIT,
        offset: 0,
      });
      setRecords(list);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Audit-Records konnten nicht geladen werden."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  async function handleCreate() {
    setCreateLoading(true);
    setError(null);
    setCreatedId(null);
    try {
      const record = await createBoardReportAuditRecord({
        purpose: "Board-Report Audit (EU AI Act / NIS2 / ISO 42001)",
        status: "draft",
        linked_export_job_ids: [],
      });
      setCreatedId(record.id);
      await loadRecords();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Audit-Record konnte nicht angelegt werden."
      );
    } finally {
      setCreateLoading(false);
    }
  }

  return (
    <section
      aria-label="Audit-Ready"
      className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
    >
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-600">
        Audit-Ready (Prüfungsdokumentation)
      </h2>
      <p className="mt-1 text-xs text-slate-500">
        Versionierte Audit-Records für den Board-Report und Verknüpfung mit
        Export-Jobs (DMS/DATEV) – für WP- und Prüfungsnachweise.
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={handleCreate}
          disabled={createLoading}
          className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
        >
          {createLoading
            ? "Wird angelegt…"
            : "Audit-Record für aktuellen Board-Report anlegen"}
        </button>
        <button
          type="button"
          onClick={loadRecords}
          disabled={loading}
          className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          {loading ? "Laden…" : "Letzte Audit-Records laden"}
        </button>
      </div>

      {error && (
        <div
          role="alert"
          className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
        >
          {error}
        </div>
      )}

      {createdId && (
        <p className="mt-3 text-sm text-emerald-700">
          Audit-Record angelegt (ID: {createdId.slice(0, 8)}…).
        </p>
      )}

      {records.length > 0 && (
        <div className="mt-4">
          <h3 className="text-xs font-semibold uppercase text-slate-500">
            Letzte {LIST_LIMIT} Audit-Records
          </h3>
          <ul className="mt-2 space-y-2">
            {records.map((r) => (
              <li
                key={r.id}
                className="rounded-lg border border-slate-100 bg-slate-50/50 px-3 py-2 text-sm"
              >
                <span className="font-medium text-slate-800">{r.purpose}</span>
                <span className="mx-2 text-slate-400">·</span>
                <span className="text-slate-600">
                  {formatDate(r.created_at)} · Version {r.report_version}
                </span>
                {r.linked_export_job_ids.length > 0 && (
                  <span className="ml-2 text-slate-500">
                    · {r.linked_export_job_ids.length} Export
                    {r.linked_export_job_ids.length !== 1 ? "e" : ""} verknüpft
                  </span>
                )}
                <span
                  className={`ml-2 rounded px-1.5 py-0.5 text-xs ${
                    r.status === "final"
                      ? "bg-emerald-100 text-emerald-800"
                      : "bg-slate-200 text-slate-700"
                  }`}
                >
                  {r.status}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
