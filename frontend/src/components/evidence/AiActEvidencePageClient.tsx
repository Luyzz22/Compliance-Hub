"use client";

import Link from "next/link";
import React, { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";

import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import {
  type AiActEvidenceFilterQuery,
  type AiEvidenceEventDetailDto,
  type AiEvidenceEventListItemDto,
  type AiEvidenceExportFormat,
  downloadAiActEvidenceExport,
  fetchAiActEvidenceEventDetail,
  fetchAiActEvidenceEvents,
} from "@/lib/api";
import {
  CH_BTN_GHOST,
  CH_BTN_PRIMARY,
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_PAGE_NAV_LINK,
  CH_SECTION_LABEL,
  CH_SHELL,
} from "@/lib/boardLayout";

type EventGroupId = "all" | "rag" | "board_report" | "llm_violation";

const EVENT_GROUPS: { id: EventGroupId; label: string }[] = [
  { id: "all", label: "Alle Typen" },
  { id: "rag", label: "RAG" },
  { id: "board_report", label: "Board-Report" },
  { id: "llm_violation", label: "LLM-Verstöße / Guardrails" },
];

function eventTypesParamForGroup(group: EventGroupId): string | undefined {
  if (group === "all") {
    return undefined;
  }
  if (group === "rag") {
    return "rag_query";
  }
  if (group === "board_report") {
    return "board_report_workflow_started,board_report_completed";
  }
  return "llm_contract_violation,llm_guardrail_block";
}

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

function toDatetimeLocalValue(d: Date): string {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}T${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}

function fromDatetimeLocalToIso(s: string): string | undefined {
  if (!s.trim()) {
    return undefined;
  }
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) {
    return undefined;
  }
  return d.toISOString();
}

function formatEventTypeDe(t: string): string {
  const m: Record<string, string> = {
    rag_query: "RAG",
    board_report_workflow_started: "Board-Report (Workflow)",
    board_report_completed: "Board-Report (fertig)",
    llm_contract_violation: "LLM-Vertrag",
    llm_guardrail_block: "Guardrail / Block",
  };
  return m[t] ?? t;
}

function shortenTraceId(id: string): string {
  if (id.length <= 14) {
    return id;
  }
  return `${id.slice(0, 8)}…${id.slice(-4)}`;
}

function observabilityTraceHref(traceId: string): string {
  const t = process.env.NEXT_PUBLIC_OBSERVABILITY_TRACE_URL_TEMPLATE?.trim();
  if (t && t.includes("{trace_id}")) {
    return t.replace(/\{trace_id\}/g, encodeURIComponent(traceId));
  }
  return `#trace-placeholder`;
}

function formatTs(iso: string): string {
  try {
    return new Date(iso).toLocaleString("de-DE", {
      dateStyle: "short",
      timeStyle: "medium",
    });
  } catch {
    return iso;
  }
}

type Props = { tenantId: string };

const PAGE_SIZE = 50;

export function AiActEvidencePageClient({ tenantId }: Props) {
  const titleId = useId();
  const [fromLocal, setFromLocal] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    return toDatetimeLocalValue(d);
  });
  const [toLocal, setToLocal] = useState(() => toDatetimeLocalValue(new Date()));
  const [eventGroup, setEventGroup] = useState<EventGroupId>("all");
  const [confidence, setConfidence] = useState<"all" | "high" | "medium" | "low">("all");
  const [page, setPage] = useState(0);

  const [applied, setApplied] = useState(() => ({
    from_ts: fromDatetimeLocalToIso(fromLocal),
    to_ts: fromDatetimeLocalToIso(toLocal),
    event_types: eventTypesParamForGroup("all"),
    confidence_level: undefined as string | undefined,
  }));

  const [rows, setRows] = useState<AiEvidenceEventListItemDto[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AiEvidenceEventDetailDto | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const [exportOpen, setExportOpen] = useState(false);
  const [exportFormat, setExportFormat] = useState<AiEvidenceExportFormat>("csv");
  const [exportBusy, setExportBusy] = useState(false);

  const drawerCloseRef = useRef<HTMLButtonElement>(null);
  const lastRowTriggerRef = useRef<HTMLElement | null>(null);

  const listQuery = useMemo(
    () => ({
      from_ts: applied.from_ts,
      to_ts: applied.to_ts,
      event_types: applied.event_types,
      confidence_level: applied.confidence_level,
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
    }),
    [applied, page],
  );

  const filterForExport: AiActEvidenceFilterQuery = useMemo(
    () => ({
      from_ts: applied.from_ts,
      to_ts: applied.to_ts,
      event_types: applied.event_types,
      confidence_level: applied.confidence_level,
    }),
    [applied],
  );

  const loadList = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchAiActEvidenceEvents(tenantId, listQuery);
      setRows(res.items);
      setTotal(res.total);
    } catch (e) {
      setRows([]);
      setTotal(0);
      setError(
        e instanceof Error
          ? e.message
          : "Ereignisse konnten nicht geladen werden. Prüfen Sie Berechtigung und Feature-Schalter.",
      );
    } finally {
      setLoading(false);
    }
  }, [tenantId, listQuery]);

  useEffect(() => {
    void loadList();
  }, [loadList]);

  const applyFilters = () => {
    setPage(0);
    setApplied({
      from_ts: fromDatetimeLocalToIso(fromLocal),
      to_ts: fromDatetimeLocalToIso(toLocal),
      event_types: eventTypesParamForGroup(eventGroup),
      confidence_level: confidence === "all" ? undefined : confidence,
    });
  };

  const openDetail = (row: AiEvidenceEventListItemDto, el: HTMLElement | null) => {
    lastRowTriggerRef.current = el;
    setSelectedId(row.event_id);
    setDetail(null);
    setDetailError(null);
  };

  useEffect(() => {
    if (!selectedId) {
      return;
    }
    let cancelled = false;
    setDetailLoading(true);
    void (async () => {
      try {
        const d = await fetchAiActEvidenceEventDetail(tenantId, selectedId);
        if (!cancelled) {
          setDetail(d);
        }
      } catch (e) {
        if (!cancelled) {
          setDetailError(
            e instanceof Error ? e.message : "Detail konnte nicht geladen werden.",
          );
        }
      } finally {
        if (!cancelled) {
          setDetailLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedId, tenantId]);

  useEffect(() => {
    if (selectedId) {
      drawerCloseRef.current?.focus();
    } else if (lastRowTriggerRef.current) {
      lastRowTriggerRef.current.focus();
    }
  }, [selectedId]);

  useEffect(() => {
    if (!selectedId) {
      return;
    }
    const onKey = (ev: KeyboardEvent) => {
      if (ev.key === "Escape") {
        setSelectedId(null);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedId]);

  const closeDrawer = () => setSelectedId(null);

  const runExport = async () => {
    setExportBusy(true);
    try {
      const blob = await downloadAiActEvidenceExport(tenantId, exportFormat, filterForExport);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = exportFormat === "json" ? "ai_act_evidence.json" : "ai_act_evidence.csv";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setExportOpen(false);
    } catch (e) {
      window.alert(
        e instanceof Error
          ? e.message
          : "Export fehlgeschlagen. Prüfen Sie Filter und Berechtigungen.",
      );
    } finally {
      setExportBusy(false);
    }
  };

  const maxPage = Math.max(0, Math.ceil(total / PAGE_SIZE) - 1);

  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        eyebrow="Compliance / Evidence"
        title="EU AI Act – KI-Evidenz"
        description={
          <>
            Schreibgeschützte Übersicht zu RAG-, Board-Report- und LLM-Guardrail-Ereignissen für
            Revision und AI-Act-Nachweise. API-Felder bleiben englisch (Backend-Vertrag).
          </>
        }
        actions={
          <>
            <button
              type="button"
              className={CH_BTN_SECONDARY}
              onClick={() => setExportOpen(true)}
            >
              Export
            </button>
            <Link href="/tenant/audit-log" className={CH_PAGE_NAV_LINK}>
              Audit-Log
            </Link>
          </>
        }
      />

      <p className="text-xs leading-relaxed text-slate-500">
        Hinweis: Exporte und diese Ansicht enthalten keine Roh-Prompts und keine personenbezogenen
        Inhalte – nur Metadaten für Prüfungen (Konfidenz, trace_id, Zitat-Referenzen, Ablauf).
      </p>

      <section className={`${CH_CARD} space-y-4`} aria-label="Filter">
        <p className={CH_SECTION_LABEL}>Filter</p>
        <div className="flex flex-col gap-4 lg:flex-row lg:flex-wrap lg:items-end">
          <label className="flex min-w-[10rem] flex-col gap-1 text-sm">
            <span className="text-slate-600">Von (lokal)</span>
            <input
              type="datetime-local"
              value={fromLocal}
              onChange={(e) => setFromLocal(e.target.value)}
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900"
            />
          </label>
          <label className="flex min-w-[10rem] flex-col gap-1 text-sm">
            <span className="text-slate-600">Bis (lokal)</span>
            <input
              type="datetime-local"
              value={toLocal}
              onChange={(e) => setToLocal(e.target.value)}
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900"
            />
          </label>
          <label className="flex min-w-[12rem] flex-col gap-1 text-sm">
            <span className="text-slate-600">Ereignistyp</span>
            <select
              value={eventGroup}
              onChange={(e) => setEventGroup(e.target.value as EventGroupId)}
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900"
            >
              {EVENT_GROUPS.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.label}
                </option>
              ))}
            </select>
          </label>
          <label className="flex min-w-[10rem] flex-col gap-1 text-sm">
            <span className="text-slate-600">Konfidenz (nur RAG)</span>
            <select
              value={confidence}
              onChange={(e) => setConfidence(e.target.value as typeof confidence)}
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900"
            >
              <option value="all">Alle</option>
              <option value="high">high</option>
              <option value="medium">medium</option>
              <option value="low">low</option>
            </select>
          </label>
          <button type="button" className={CH_BTN_PRIMARY} onClick={applyFilters}>
            Filter anwenden
          </button>
        </div>
      </section>

      <section className={`${CH_CARD} overflow-x-auto p-0`} aria-labelledby={titleId}>
        <div className="flex items-center justify-between border-b border-slate-200/80 px-5 py-4">
          <h2 id={titleId} className="text-sm font-semibold text-slate-900">
            Ereignisse
          </h2>
          <span className="text-xs text-slate-500">
            {total} Treffer · Mandant{" "}
            <span className="font-mono text-slate-700">{tenantId}</span>
          </span>
        </div>

        {loading ? (
          <p className="px-5 py-10 text-sm text-slate-600" role="status">
            Daten werden geladen …
          </p>
        ) : error ? (
          <p className="px-5 py-10 text-sm text-red-800" role="alert">
            {error}
          </p>
        ) : rows.length === 0 ? (
          <p className="px-5 py-10 text-sm text-slate-600" role="status">
            Keine Ereignisse für die gewählten Filter.
          </p>
        ) : (
          <table className="min-w-full border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/90 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <th scope="col" className="px-4 py-3">
                  Zeit
                </th>
                <th scope="col" className="px-4 py-3">
                  Typ
                </th>
                <th scope="col" className="px-4 py-3">
                  Quelle
                </th>
                <th scope="col" className="px-4 py-3">
                  Rolle
                </th>
                <th scope="col" className="px-4 py-3">
                  Konfidenz
                </th>
                <th scope="col" className="px-4 py-3">
                  Kurztext
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={row.event_id}
                  className="border-b border-slate-100 hover:bg-cyan-50/40 focus-within:bg-cyan-50/50"
                >
                  <td className="max-w-[12rem] whitespace-nowrap px-4 py-3 text-slate-700">
                    {formatTs(row.timestamp)}
                  </td>
                  <td className="px-4 py-3 text-slate-800">{formatEventTypeDe(row.event_type)}</td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-600">{row.source}</td>
                  <td className="px-4 py-3 text-slate-700">{row.user_role}</td>
                  <td className="px-4 py-3 text-slate-600">
                    {row.confidence_level ?? "—"}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      className={`${CH_BTN_GHOST} max-w-full text-left text-sm font-normal text-cyan-800 underline decoration-cyan-600/30`}
                      onClick={(e) => openDetail(row, e.currentTarget)}
                      aria-label={`Details zu ${row.event_id}`}
                    >
                      <span className="line-clamp-2">{row.summary_de}</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {!loading && !error && total > PAGE_SIZE ? (
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-200/80 px-5 py-4">
            <span className="text-xs text-slate-600">
              Seite {page + 1} von {maxPage + 1}
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                className={CH_BTN_SECONDARY}
                disabled={page <= 0}
                onClick={() => setPage((p) => Math.max(0, p - 1))}
              >
                Zurück
              </button>
              <button
                type="button"
                className={CH_BTN_SECONDARY}
                disabled={page >= maxPage}
                onClick={() => setPage((p) => p + 1)}
              >
                Weiter
              </button>
            </div>
          </div>
        ) : null}
      </section>

      {exportOpen ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
          role="presentation"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) {
              setExportOpen(false);
            }
          }}
        >
          <div
            className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl"
            role="dialog"
            aria-modal="true"
            aria-labelledby="export-dialog-title"
          >
            <h2 id="export-dialog-title" className="text-lg font-semibold text-slate-900">
              Evidence exportieren
            </h2>
            <p className="mt-2 text-sm text-slate-600">
              Es werden die aktuell gesetzten Filter verwendet (keine Roh-Prompts, keine PII).
            </p>
            <label className="mt-4 flex flex-col gap-1 text-sm">
              <span className="text-slate-600">Format</span>
              <select
                value={exportFormat}
                onChange={(e) => setExportFormat(e.target.value as AiEvidenceExportFormat)}
                className="rounded-lg border border-slate-200 px-3 py-2"
              >
                <option value="csv">CSV</option>
                <option value="json">JSON</option>
              </select>
            </label>
            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                className={CH_BTN_GHOST}
                onClick={() => setExportOpen(false)}
                disabled={exportBusy}
              >
                Abbrechen
              </button>
              <button
                type="button"
                className={CH_BTN_PRIMARY}
                onClick={() => void runExport()}
                disabled={exportBusy}
              >
                {exportBusy ? "Export …" : "Herunterladen"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {selectedId ? (
        <>
          <button
            type="button"
            className="fixed inset-0 z-40 bg-slate-900/30"
            aria-label="Detail schließen"
            onClick={closeDrawer}
          />
          <aside
            className="fixed inset-y-0 right-0 z-50 flex w-full max-w-lg flex-col border-l border-slate-200 bg-white shadow-2xl"
            role="dialog"
            aria-modal="true"
            aria-labelledby="evidence-detail-title"
          >
            <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
              <h2 id="evidence-detail-title" className="text-base font-semibold text-slate-900">
                Ereignisdetails
              </h2>
              <button
                ref={drawerCloseRef}
                type="button"
                className={CH_BTN_GHOST}
                onClick={closeDrawer}
              >
                Schließen
              </button>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4 text-sm">
              {detailLoading ? (
                <p role="status">Details werden geladen …</p>
              ) : detailError ? (
                <p className="text-red-800" role="alert">
                  {detailError}
                </p>
              ) : detail ? (
                <DetailBody detail={detail} />
              ) : null}
            </div>
          </aside>
        </>
      ) : null}
    </div>
  );
}

function DetailBody({ detail }: { detail: AiEvidenceEventDetailDto }) {
  const trace =
    detail.rag?.trace_id ||
    (detail.board_report_completed?.temporal_workflow_id
      ? `workflow:${detail.board_report_completed.temporal_workflow_id}`
      : null);

  return (
    <div className="space-y-5">
      <dl className="space-y-2">
        <div>
          <dt className="text-xs font-semibold uppercase text-slate-500">tenant_id</dt>
          <dd className="font-mono text-slate-900">{detail.tenant_id}</dd>
        </div>
        <div>
          <dt className="text-xs font-semibold uppercase text-slate-500">Zeitstempel</dt>
          <dd className="text-slate-800">{formatTs(detail.timestamp)}</dd>
        </div>
        <div>
          <dt className="text-xs font-semibold uppercase text-slate-500">event_type</dt>
          <dd className="text-slate-800">{formatEventTypeDe(detail.event_type)}</dd>
        </div>
        <div>
          <dt className="text-xs font-semibold uppercase text-slate-500">event_id</dt>
          <dd className="break-all font-mono text-xs text-slate-800">{detail.event_id}</dd>
        </div>
        {trace ? (
          <div>
            <dt className="text-xs font-semibold uppercase text-slate-500">trace_id</dt>
            <dd className="font-mono text-xs text-slate-800">
              {detail.rag?.trace_id ? shortenTraceId(detail.rag.trace_id) : trace}
            </dd>
            {detail.rag?.trace_id ? (
              <a
                href={observabilityTraceHref(detail.rag.trace_id)}
                className={`${CH_PAGE_NAV_LINK} mt-1 inline-block text-xs`}
                target="_blank"
                rel="noreferrer"
              >
                Trace im Observability-Tool (Platzhalter-Link)
              </a>
            ) : null}
          </div>
        ) : (
          <div>
            <dt className="text-xs font-semibold uppercase text-slate-500">trace_id</dt>
            <dd className="text-slate-500">—</dd>
          </div>
        )}
      </dl>

      <div>
        <p className="text-xs font-semibold uppercase text-slate-500">Kurztext</p>
        <p className="mt-1 text-slate-800">{detail.summary_de}</p>
      </div>

      {detail.rag ? (
        <section className="rounded-xl border border-slate-200 bg-slate-50/80 p-4">
          <p className="text-xs font-semibold uppercase text-slate-500">RAG (ohne Frage/Antwort)</p>
          <ul className="mt-2 list-inside list-disc space-y-1 text-slate-700">
            <li>
              Konfidenz: <span className="font-mono">{detail.rag.confidence_level ?? "—"}</span>
            </li>
            <li>Zitate gesamt: {detail.rag.citation_count}</li>
            <li>
              Mandanten-Leitfaden (Zitate): {detail.rag.tenant_guidance_citation_count} · Globale
              Normenkorpus-Referenzen (doc_id): {detail.rag.citation_doc_ids.length}
            </li>
          </ul>
          {detail.rag.citation_doc_ids.length > 0 ? (
            <ul className="mt-2 max-h-40 overflow-y-auto rounded border border-slate-200 bg-white p-2 font-mono text-xs text-slate-700">
              {detail.rag.citation_doc_ids.map((id) => (
                <li key={id}>{id}</li>
              ))}
            </ul>
          ) : null}
          {detail.rag.query_sha256 ? (
            <p className="mt-2 text-xs text-slate-500">
              query_sha256: <span className="font-mono">{detail.rag.query_sha256}</span>
            </p>
          ) : null}
        </section>
      ) : null}

      {detail.board_report_workflow ? (
        <section className="rounded-xl border border-slate-200 bg-slate-50/80 p-4">
          <p className="text-xs font-semibold uppercase text-slate-500">Board-Report (Workflow)</p>
          <ul className="mt-2 space-y-1 text-slate-700">
            <li>workflow_id: {detail.board_report_workflow.workflow_id}</li>
            <li>task_queue: {detail.board_report_workflow.task_queue ?? "—"}</li>
            <li>status_hint: {detail.board_report_workflow.status_hint ?? "—"}</li>
          </ul>
          <p className="mt-2 text-xs text-slate-500">
            LLM-Contract-Violations werden als eigene Ereignistypen gelistet; dieses Event enthält
            keine Roh-Ausgabe.
          </p>
        </section>
      ) : null}

      {detail.board_report_completed ? (
        <section className="rounded-xl border border-slate-200 bg-slate-50/80 p-4">
          <p className="text-xs font-semibold uppercase text-slate-500">Board-Report (abgeschlossen)</p>
          <ul className="mt-2 space-y-1 text-slate-700">
            <li>title: {detail.board_report_completed.title}</li>
            <li>report_id: {detail.board_report_completed.report_id}</li>
            <li>audience_type: {detail.board_report_completed.audience_type}</li>
            <li>
              temporal_workflow_id: {detail.board_report_completed.temporal_workflow_id ?? "—"}
            </li>
            <li>temporal_run_id: {detail.board_report_completed.temporal_run_id ?? "—"}</li>
          </ul>
          <p className="mt-2 text-xs font-semibold uppercase text-slate-500">Aktivitäten</p>
          <ul className="list-inside list-disc text-slate-700">
            {detail.board_report_completed.activities_executed.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {detail.llm ? (
        <section className="rounded-xl border border-slate-200 bg-slate-50/80 p-4">
          <p className="text-xs font-semibold uppercase text-slate-500">LLM / Guardrails</p>
          <ul className="mt-2 space-y-1 text-slate-700">
            <li>contract_schema: {detail.llm.contract_schema ?? "—"}</li>
            <li>error_class: {detail.llm.error_class ?? "—"}</li>
            <li>action_name: {detail.llm.action_name ?? "—"}</li>
            <li>task_type: {detail.llm.task_type ?? "—"}</li>
          </ul>
          {detail.llm.guardrail_flags && Object.keys(detail.llm.guardrail_flags).length > 0 ? (
            <>
              <p className="mt-2 text-xs font-semibold uppercase text-slate-500">guardrail_flags</p>
              <pre className="mt-1 overflow-x-auto rounded border border-slate-200 bg-white p-2 text-xs">
                {JSON.stringify(detail.llm.guardrail_flags, null, 2)}
              </pre>
            </>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
