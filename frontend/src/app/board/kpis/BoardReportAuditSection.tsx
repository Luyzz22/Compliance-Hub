"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  createBoardReportAuditRecord,
  fetchNormEvidenceDefaults,
  fetchBoardReportAuditRecords,
  createNormEvidence,
  fetchNormEvidenceByAudit,
  fetchHighRiskScenarios,
  type BoardReportAuditRecord,
  type NormEvidenceLink,
  type NormFramework,
  type NormEvidenceSuggestion,
  type HighRiskScenarioProfile,
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
  const [defaults, setDefaults] = useState<NormEvidenceSuggestion[] | null>(null);
  const [highRiskScenarios, setHighRiskScenarios] = useState<
    HighRiskScenarioProfile[] | null
  >(null);
  const [highRiskLoading, setHighRiskLoading] = useState(false);
  const [expandedHighRiskId, setExpandedHighRiskId] = useState<string | null>(
    null,
  );
  const [scenarioTargetAuditId, setScenarioTargetAuditId] = useState<
    string | null
  >(null);
  const [loading, setLoading] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdId, setCreatedId] = useState<string | null>(null);

  useEffect(() => {
    if (records.length === 0) {
      setScenarioTargetAuditId(null);
      return;
    }
    setScenarioTargetAuditId((prev) =>
      prev && records.some((r) => r.id === prev) ? prev : records[0].id,
    );
  }, [records]);

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
      className="sbs-panel p-4"
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

      <div className="mt-5 rounded-xl border border-amber-100 bg-amber-50/40 p-3">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-amber-900/90">
          High-Risk-AI-Szenarien
        </h3>
        <p className="mt-1 text-[11px] leading-snug text-amber-950/80">
          Empfohlene Norm-Nachweise für High-Risk-AI-Szenarien (EU AI Act / NIS2 /
          ISO 42001) – werden erst beim Speichern angelegt.
        </p>
        {records.length > 0 && scenarioTargetAuditId && (
          <label className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-slate-700">
            <span className="font-medium">Ziel-Audit-Record für „Übernehmen“:</span>
            <select
              value={scenarioTargetAuditId}
              onChange={(e) => setScenarioTargetAuditId(e.target.value)}
              className="max-w-full rounded border border-slate-300 bg-white px-2 py-1 text-xs"
            >
              {records.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.purpose.slice(0, 48)}
                  {r.purpose.length > 48 ? "…" : ""} ({r.id.slice(0, 8)}…)
                </option>
              ))}
            </select>
          </label>
        )}
        {records.length === 0 && (
          <p className="mt-2 text-[11px] text-slate-600">
            Bitte zuerst Audit-Records laden oder anlegen, um Vorschläge in ein
            Formular zu übernehmen.
          </p>
        )}
        {highRiskScenarios === null && !highRiskLoading && (
          <div className="mt-2">
            <button
              type="button"
              onClick={async () => {
                setHighRiskLoading(true);
                setError(null);
                try {
                  const list = await fetchHighRiskScenarios();
                  setHighRiskScenarios(list);
                } catch (err) {
                  setError(
                    err instanceof Error
                      ? err.message
                      : "High-Risk-Szenarien konnten nicht geladen werden.",
                  );
                } finally {
                  setHighRiskLoading(false);
                }
              }}
              className="rounded-lg border border-amber-300/80 bg-white px-3 py-1.5 text-xs font-medium text-amber-950 hover:bg-amber-100/80"
            >
              High-Risk-Szenarien &amp; Empfehlungen laden
            </button>
          </div>
        )}
        {highRiskLoading && (
          <p className="mt-2 text-[11px] text-slate-600">Laden…</p>
        )}
        {highRiskScenarios && highRiskScenarios.length > 0 && (
          <ul className="mt-3 space-y-2">
            {highRiskScenarios.map((s) => (
              <li
                key={s.id}
                className="rounded-lg border border-slate-200 bg-white/90 p-2 text-sm"
              >
                <div className="font-medium text-slate-800">{s.label}</div>
                <p className="mt-0.5 text-[11px] text-slate-600">
                  {s.description}
                </p>
                <button
                  type="button"
                  onClick={() =>
                    setExpandedHighRiskId((prev) =>
                      prev === s.id ? null : s.id,
                    )
                  }
                  className="mt-2 text-[11px] font-medium text-amber-900 underline decoration-amber-700/50 hover:text-amber-950"
                >
                  {expandedHighRiskId === s.id
                    ? "Empfohlene Norm-Nachweise ausblenden"
                    : "Empfohlene Norm-Nachweise anzeigen/übernehmen"}
                </button>
                {expandedHighRiskId === s.id && (
                  <ul className="mt-2 flex flex-col gap-1.5">
                    {s.recommended_evidence.map((ev, idx) => (
                      <li
                        key={`${s.id}-${ev.framework}-${ev.reference}-${idx}`}
                        className="flex flex-wrap items-start justify-between gap-2 rounded border border-slate-100 bg-slate-50/80 px-2 py-1.5 text-[11px]"
                      >
                        <div className="min-w-0 flex-1">
                          <span className="font-semibold text-slate-800">
                            {ev.framework}
                          </span>{" "}
                          <span className="text-slate-700">{ev.reference}</span>
                          {ev.note && (
                            <span className="mt-0.5 block text-slate-600">
                              {ev.note}
                            </span>
                          )}
                        </div>
                        <button
                          type="button"
                          disabled={!scenarioTargetAuditId}
                          onClick={() => {
                            if (!scenarioTargetAuditId) return;
                            setNormForm((prev) => ({
                              ...prev,
                              [scenarioTargetAuditId]: {
                                framework: ev.framework,
                                reference: ev.reference,
                                note: ev.note ?? "",
                              },
                            }));
                          }}
                          className="shrink-0 rounded border border-slate-300 bg-white px-2 py-0.5 text-[11px] font-medium text-slate-800 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          Übernehmen
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

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
                        if (defaults === null) {
                          const def = await fetchNormEvidenceDefaults();
                          setDefaults(def);
                        }
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
                  {defaults && defaults.length > 0 && (
                    <div className="mt-2 rounded border border-slate-100 bg-white p-2">
                      <p className="text-[11px] font-semibold text-slate-600">
                        Empfohlene Norm-Nachweise für Board-Reports
                      </p>
                      <ul className="mt-1 flex flex-wrap gap-1">
                        {defaults.map((d) => (
                          <li key={`${d.framework}-${d.reference}`}>
                            <button
                              type="button"
                              onClick={() => {
                                setNormForm((prev) => ({
                                  ...prev,
                                  [r.id]: {
                                    framework: d.framework,
                                    reference: d.reference,
                                    note: d.note ?? "",
                                  },
                                }));
                              }}
                              className="rounded border border-slate-200 bg-slate-50 px-2 py-1 text-[11px] text-slate-700 hover:bg-slate-100"
                              title={d.note ?? ""}
                            >
                              Übernehmen: {d.framework} – {d.reference}
                            </button>
                          </li>
                        ))}
                      </ul>
                      <p className="mt-1 text-[11px] text-slate-500">
                        Hinweis: „Übernehmen“ füllt nur das Formular. Erst
                        „Hinzufügen“ legt einen echten Norm-Nachweis an.
                      </p>
                    </div>
                  )}
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
