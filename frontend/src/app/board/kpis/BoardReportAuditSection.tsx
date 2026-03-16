"use client";

import React, { useCallback, useState } from "react";
import {
  createBoardReportAuditRecord,
  fetchBoardReportAuditRecords,
  createNormEvidence,
  fetchNormEvidenceByAudit,
  type BoardReportAuditRecord,
  type NormEvidenceLink,
  type NormFramework,
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
  const [normEvidence, setNormEvidence] = useState<
    Record<string, NormEvidenceLink[]>
  >({});
  const [normForm, setNormForm] = useState<{
    [auditId: string]: { framework: NormFramework; reference: string; note: string };
  }>({});
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
      // Norm-Nachweise zurücksetzen (bei Bedarf neu laden)
      setNormEvidence({});
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
                {/* Norm-Nachweise */}
                <div className="mt-2 space-y-1">
                  <button
                    type="button"
                    onClick={async () => {
                      try {
                        const items = await fetchNormEvidenceByAudit(r.id);
                        setNormEvidence((prev) => ({
                          ...prev,
                          [r.id]: items,
                        }));
                      } catch (err) {
                        setError(
                          err instanceof Error
                            ? err.message
                            : "Norm-Nachweise konnten nicht geladen werden.",
                        );
                      }
                    }}
                    className="text-xs font-medium text-slate-600 underline hover:text-slate-900"
                  >
                    Norm-Nachweise anzeigen
                  </button>
                  {normEvidence[r.id] && normEvidence[r.id].length > 0 && (
                    <ul className="mt-1 space-y-0.5 text-xs text-slate-600">
                      {normEvidence[r.id].map((ev) => (
                        <li key={ev.id}>
                          <span className="font-semibold">{ev.framework}</span>{" "}
                          {ev.reference}
                          {ev.note && <> – {ev.note}</>}
                        </li>
                      ))}
                    </ul>
                  )}
                  {/* Formular für neuen Norm-Nachweis */}
                  <div className="mt-2 grid gap-1 text-xs sm:grid-cols-3">
                    <select
                      value={normForm[r.id]?.framework ?? "EU_AI_ACT"}
                      onChange={(e) =>
                        setNormForm((prev) => ({
                          ...prev,
                          [r.id]: {
                            framework: e.target.value as NormFramework,
                            reference: prev[r.id]?.reference ?? "",
                            note: prev[r.id]?.note ?? "",
                          },
                        }))
                      }
                      className="rounded border border-slate-300 bg-white px-1.5 py-1"
                    >
                      <option value="EU_AI_ACT">EU AI Act</option>
                      <option value="NIS2">NIS2</option>
                      <option value="ISO_42001">ISO 42001</option>
                    </select>
                    <input
                      type="text"
                      placeholder="Referenz (z. B. Art. 9)"
                      value={normForm[r.id]?.reference ?? ""}
                      onChange={(e) =>
                        setNormForm((prev) => ({
                          ...prev,
                          [r.id]: {
                            framework: prev[r.id]?.framework ?? "EU_AI_ACT",
                            reference: e.target.value,
                            note: prev[r.id]?.note ?? "",
                          },
                        }))
                      }
                      className="rounded border border-slate-300 bg-white px-1.5 py-1"
                    />
                    <div className="flex gap-1">
                      <input
                        type="text"
                        placeholder="Notiz (optional)"
                        value={normForm[r.id]?.note ?? ""}
                        onChange={(e) =>
                          setNormForm((prev) => ({
                            ...prev,
                            [r.id]: {
                              framework: prev[r.id]?.framework ?? "EU_AI_ACT",
                              reference: prev[r.id]?.reference ?? "",
                              note: e.target.value,
                            },
                          }))
                        }
                        className="flex-1 rounded border border-slate-300 bg-white px-1.5 py-1"
                      />
                      <button
                        type="button"
                        onClick={async () => {
                          const current = normForm[r.id] ?? {
                            framework: "EU_AI_ACT" as NormFramework,
                            reference: "",
                            note: "",
                          };
                          if (!current.reference.trim()) {
                            setError(
                              "Bitte eine Norm-Referenz (z. B. Art. 9) angeben.",
                            );
                            return;
                          }
                          setError(null);
                          try {
                            await createNormEvidence(r.id, {
                              framework: current.framework,
                              reference: current.reference.trim(),
                              evidence_type: "board_report",
                              note: current.note?.trim() || undefined,
                            });
                            const items = await fetchNormEvidenceByAudit(r.id);
                            setNormEvidence((prev) => ({
                              ...prev,
                              [r.id]: items,
                            }));
                          } catch (err) {
                            setError(
                              err instanceof Error
                                ? err.message
                                : "Norm-Nachweis konnte nicht angelegt werden.",
                            );
                          }
                        }}
                        className="rounded bg-slate-800 px-2 py-1 text-[11px] font-medium text-white hover:bg-slate-700"
                      >
                        Hinzufügen
                      </button>
                    </div>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
