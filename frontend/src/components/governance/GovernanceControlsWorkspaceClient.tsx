"use client";

import { useCallback, useEffect, useState } from "react";

import { GovernanceWorkspaceLayout } from "@/components/governance/GovernanceWorkspaceLayout";
import {
  downloadControlsCsv,
  fetchControlEvidence,
  fetchControlStatusHistory,
  fetchControlsDashboardSummary,
  fetchControlSuggestions,
  fetchGovernanceControls,
  postControlEvidence,
  postMaterializeSuggestion,
  type ControlsDashboardSummary,
  type FrameworkFilterTag,
  type GovernanceControlEvidenceRow,
  type GovernanceControlRow,
  type GovernanceControlStatusHistoryRow,
  type GovernanceControlSuggestion,
} from "@/lib/governanceControlsApi";
import { CH_BTN_PRIMARY, CH_BTN_SECONDARY, CH_CARD, CH_SECTION_LABEL } from "@/lib/boardLayout";

const FRAMEWORK_FILTERS: Array<{ id: FrameworkFilterTag | "ALL"; label: string }> = [
  { id: "ALL", label: "Alle" },
  { id: "EU_AI_ACT", label: "EU AI Act" },
  { id: "ISO_42001", label: "ISO 42001" },
  { id: "ISO_27001", label: "ISO 27001" },
  { id: "ISO_27701", label: "ISO 27701" },
  { id: "NIS2", label: "NIS2 / KRITIS" },
];

const PAGE_SIZE = 50;

interface Props {
  tenantId: string;
}

function statusPillClass(status: string): string {
  if (status === "implemented") {
    return "bg-emerald-100 text-emerald-900 ring-emerald-200/80";
  }
  if (status === "in_progress") {
    return "bg-sky-100 text-sky-950 ring-sky-200/80";
  }
  if (status === "overdue" || status === "needs_review") {
    return "bg-amber-100 text-amber-950 ring-amber-200/80";
  }
  return "bg-slate-100 text-slate-800 ring-slate-200/80";
}

export function GovernanceControlsWorkspaceClient({ tenantId }: Props) {
  const [summary, setSummary] = useState<ControlsDashboardSummary | null>(null);
  const [rows, setRows] = useState<GovernanceControlRow[]>([]);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState<FrameworkFilterTag | "ALL">("ALL");
  const [searchInput, setSearchInput] = useState("");
  const [searchDebounced, setSearchDebounced] = useState("");
  const [suggestions, setSuggestions] = useState<GovernanceControlSuggestion[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<GovernanceControlEvidenceRow[]>([]);
  const [history, setHistory] = useState<GovernanceControlStatusHistoryRow[]>([]);
  const [detailTab, setDetailTab] = useState<"evidence" | "history">("evidence");
  const [evidenceModalOpen, setEvidenceModalOpen] = useState(false);
  const [evTitle, setEvTitle] = useState("");
  const [evBody, setEvBody] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const t = window.setTimeout(() => setSearchDebounced(searchInput), 400);
    return () => window.clearTimeout(t);
  }, [searchInput]);

  useEffect(() => {
    if (!evidenceModalOpen) {
      return;
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setEvidenceModalOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [evidenceModalOpen]);

  const loadList = useCallback(
    async (append: boolean) => {
      setError(null);
      const offset = append ? rows.length : 0;
      const page = await fetchGovernanceControls(tenantId, {
        frameworkTag: filter === "ALL" ? undefined : filter,
        search: searchDebounced.trim() || undefined,
        offset,
        limit: PAGE_SIZE,
      });
      setTotal(page.total);
      setRows((prev) => (append ? [...prev, ...page.items] : page.items));
    },
    [tenantId, filter, searchDebounced, rows.length],
  );

  const reload = useCallback(async () => {
    setError(null);
    try {
      const [s, sug] = await Promise.all([
        fetchControlsDashboardSummary(tenantId),
        fetchControlSuggestions(tenantId),
      ]);
      setSummary(s);
      setSuggestions(sug);
      const page = await fetchGovernanceControls(tenantId, {
        frameworkTag: filter === "ALL" ? undefined : filter,
        search: searchDebounced.trim() || undefined,
        offset: 0,
        limit: PAGE_SIZE,
      });
      setTotal(page.total);
      setRows(page.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Laden fehlgeschlagen");
    }
  }, [tenantId, filter, searchDebounced]);

  useEffect(() => {
    void reload();
  }, [reload]);

  useEffect(() => {
    if (!selectedId) {
      setEvidence([]);
      setHistory([]);
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const [ev, hi] = await Promise.all([
          fetchControlEvidence(tenantId, selectedId),
          fetchControlStatusHistory(tenantId, selectedId),
        ]);
        if (!cancelled) {
          setEvidence(ev);
          setHistory(hi);
        }
      } catch {
        if (!cancelled) {
          setEvidence([]);
          setHistory([]);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [tenantId, selectedId]);

  const selectedRow = rows.find((r) => r.id === selectedId) ?? null;

  async function onMaterialize(key: string) {
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      await postMaterializeSuggestion(tenantId, key);
      setSuccess("Control aus Vorschlag angelegt oder bereits vorhanden.");
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Materialisierung fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  }

  async function onExport() {
    setBusy(true);
    setError(null);
    try {
      await downloadControlsCsv(tenantId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  }

  async function onSubmitEvidence() {
    const cid = selectedId;
    if (!cid || !evTitle.trim()) {
      setError("Control auswählen und Titel angeben.");
      return;
    }
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      await postControlEvidence(tenantId, cid, {
        title: evTitle.trim(),
        body_text: evBody.trim() || null,
        source_type: "manual",
      });
      setEvidenceModalOpen(false);
      setEvTitle("");
      setEvBody("");
      setSuccess("Evidence gespeichert.");
      const ev = await fetchControlEvidence(tenantId, cid);
      setEvidence(ev);
      void reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Evidence speichern fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  }

  const canLoadMore = rows.length < total;

  const dashboard = (
    <div className="space-y-8">
      {error ? (
        <p className="text-sm text-rose-800" role="alert">
          {error}
        </p>
      ) : null}
      {success ? (
        <p className="text-sm text-emerald-800" role="status">
          {success}
        </p>
      ) : null}

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <article className={`${CH_CARD} border-slate-200/80`}>
          <p className={CH_SECTION_LABEL}>Controls gesamt</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-slate-900">
            {summary?.total_controls ?? "—"}
          </p>
        </article>
        <article className={`${CH_CARD} border-slate-200/80`}>
          <p className={CH_SECTION_LABEL}>Umgesetzt</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-emerald-800">
            {summary?.implemented ?? "—"}
          </p>
        </article>
        <article className={`${CH_CARD} border-slate-200/80`}>
          <p className={CH_SECTION_LABEL}>In Arbeit</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-sky-800">
            {summary?.in_progress ?? "—"}
          </p>
        </article>
        <article className={`${CH_CARD} border-slate-200/80`}>
          <p className={CH_SECTION_LABEL}>Review fällig / Überfällig</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-amber-900">
            {(summary?.needs_review ?? 0) + (summary?.overdue_reviews ?? 0)}
          </p>
          <p className="mt-1 text-xs text-slate-600">
            needs_review {summary?.needs_review ?? 0} · overdue {summary?.overdue_reviews ?? 0}
          </p>
        </article>
        <article className={`${CH_CARD} border-slate-200/80`}>
          <p className={CH_SECTION_LABEL}>Offen</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-slate-900">
            {summary?.not_started ?? "—"}
          </p>
        </article>
      </section>

      {suggestions.length > 0 ? (
        <article className={`${CH_CARD} border-indigo-100 bg-indigo-50/40`}>
          <p className={CH_SECTION_LABEL}>Deterministische Vorschläge</p>
          <p className="mt-1 text-sm text-slate-700">
            Basierend auf NIS2/KRITIS, KI-Register und Betriebs-Health — ohne KI-Blackbox.
          </p>
          <ul className="mt-4 space-y-3">
            {suggestions.map((s) => (
              <li
                key={s.suggestion_key}
                className="flex flex-col gap-2 rounded-lg border border-indigo-100 bg-white/90 p-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <div>
                  <p className="font-semibold text-slate-900">{s.title}</p>
                  <p className="text-xs text-slate-600">{s.description}</p>
                  <p className="mt-1 text-[0.65rem] uppercase tracking-wide text-slate-500">
                    {s.framework_tags.join(" · ")}
                  </p>
                </div>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void onMaterialize(s.suggestion_key)}
                  className={CH_BTN_PRIMARY}
                >
                  Als Control anlegen
                </button>
              </li>
            ))}
          </ul>
        </article>
      ) : null}

      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Framework-Filter
          </span>
          {FRAMEWORK_FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              onClick={() => setFilter(f.id)}
              className={
                filter === f.id
                  ? "rounded-full bg-[var(--sbs-navy-mid)] px-3 py-1 text-xs font-semibold text-white"
                  : "rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
              }
            >
              {f.label}
            </button>
          ))}
        </div>
        <label className="flex min-w-[220px] flex-1 flex-col text-xs font-semibold uppercase tracking-wide text-slate-500">
          Suche (Titel)
          <input
            type="search"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="z. B. Incident, Lieferkette…"
            className="mt-1 rounded-lg border border-slate-200 px-3 py-2 text-sm font-normal text-slate-900"
          />
        </label>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={busy || !selectedId}
          onClick={() => {
            setEvTitle("");
            setEvBody("");
            setEvidenceModalOpen(true);
          }}
          className={CH_BTN_PRIMARY}
        >
          Evidence hinzufügen
        </button>
        <button type="button" onClick={() => void reload()} className={CH_BTN_SECONDARY} disabled={busy}>
          Aktualisieren
        </button>
        <button type="button" onClick={() => void onExport()} className={CH_BTN_SECONDARY} disabled={busy}>
          CSV exportieren
        </button>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_minmax(280px,340px)]">
        <article className={CH_CARD}>
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <div>
              <p className={CH_SECTION_LABEL}>Controls</p>
              <h2 className="mt-1 text-lg font-semibold text-slate-900">Map once, comply many</h2>
            </div>
            <p className="text-xs text-slate-500">
              {rows.length} von {total} geladen
            </p>
          </div>
          <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200/80">
            <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
              <thead className="bg-slate-50/90 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-3 py-2">Titel</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Owner</th>
                  <th className="px-3 py-2">Nächstes Review</th>
                  <th className="px-3 py-2">Tags</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {rows.length === 0 ? (
                  <tr>
                    <td className="px-3 py-6 text-slate-600" colSpan={5}>
                      Keine Controls — Vorschläge nutzen oder per API POST anlegen.
                    </td>
                  </tr>
                ) : (
                  rows.map((r) => (
                    <tr
                      key={r.id}
                      className={`cursor-pointer hover:bg-slate-50/80 ${
                        selectedId === r.id ? "bg-sky-50/90" : ""
                      }`}
                      onClick={() => {
                        setSelectedId(r.id);
                        setSuccess(null);
                      }}
                    >
                      <td className="px-3 py-2 font-medium text-slate-900">{r.title}</td>
                      <td className="px-3 py-2">
                        <span
                          className={`inline-flex rounded-full px-2 py-0.5 text-[0.65rem] font-semibold ring-1 ring-inset ${statusPillClass(r.status)}`}
                        >
                          {r.status}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-slate-700">{r.owner ?? "—"}</td>
                      <td className="px-3 py-2 text-slate-700">
                        {r.next_review_at
                          ? new Date(r.next_review_at).toLocaleDateString("de-DE")
                          : "—"}
                      </td>
                      <td className="px-3 py-2 text-xs text-slate-600">
                        {(r.framework_tags ?? []).join(", ") || "—"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          {canLoadMore ? (
            <div className="mt-4 flex justify-center">
              <button
                type="button"
                disabled={busy}
                onClick={() => void loadList(true)}
                className={CH_BTN_SECONDARY}
              >
                Mehr laden
              </button>
            </div>
          ) : null}
        </article>

        <aside className={`${CH_CARD} h-fit border-slate-200/80 lg:sticky lg:top-4`}>
          <p className={CH_SECTION_LABEL}>Detail</p>
          {!selectedRow ? (
            <p className="mt-2 text-sm text-slate-600">Zeile wählen für Evidence-Liste und Status-Historie.</p>
          ) : (
            <>
              <p className="mt-2 font-semibold text-slate-900">{selectedRow.title}</p>
              <p className="mt-1 font-mono text-[0.65rem] text-slate-500">{selectedRow.id}</p>
              <div className="mt-3 flex gap-1 border-b border-slate-200 pb-2">
                <button
                  type="button"
                  onClick={() => setDetailTab("evidence")}
                  className={
                    detailTab === "evidence"
                      ? "rounded-md bg-slate-900 px-2 py-1 text-xs font-semibold text-white"
                      : "rounded-md px-2 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-100"
                  }
                >
                  Evidence ({evidence.length})
                </button>
                <button
                  type="button"
                  onClick={() => setDetailTab("history")}
                  className={
                    detailTab === "history"
                      ? "rounded-md bg-slate-900 px-2 py-1 text-xs font-semibold text-white"
                      : "rounded-md px-2 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-100"
                  }
                >
                  Historie ({history.length})
                </button>
              </div>
              <ul className="mt-3 max-h-72 space-y-2 overflow-y-auto text-xs text-slate-700">
                {detailTab === "evidence"
                  ? evidence.map((e) => (
                      <li key={e.id} className="rounded border border-slate-100 bg-slate-50/80 p-2">
                        <span className="font-medium">{e.title}</span>
                        <span className="block text-slate-500">
                          {new Date(e.created_at_utc).toLocaleString("de-DE")} · {e.source_type}
                        </span>
                      </li>
                    ))
                  : history.map((h) => (
                      <li key={h.id} className="rounded border border-slate-100 bg-slate-50/80 p-2">
                        <span className="font-medium">
                          {h.from_status ?? "—"} → {h.to_status}
                        </span>
                        <span className="block text-slate-500">
                          {new Date(h.changed_at_utc).toLocaleString("de-DE")}
                          {h.changed_by ? ` · ${h.changed_by}` : ""}
                        </span>
                      </li>
                    ))}
              </ul>
            </>
          )}
        </aside>
      </div>

      {evidenceModalOpen ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="evidence-dialog-title"
          onClick={() => setEvidenceModalOpen(false)}
        >
          <div
            className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-5 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 id="evidence-dialog-title" className="text-lg font-semibold text-slate-900">
              Evidence hinzufügen
            </h3>
            <p className="mt-1 text-sm text-slate-600">
              Control: <span className="font-mono text-xs">{selectedId}</span>
            </p>
            <label className="mt-4 block text-sm font-medium text-slate-700">
              Titel
              <input
                value={evTitle}
                onChange={(e) => setEvTitle(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                placeholder="Policy, Log-Export, Protokoll…"
              />
            </label>
            <label className="mt-3 block text-sm font-medium text-slate-700">
              Beschreibung (optional)
              <textarea
                value={evBody}
                onChange={(e) => setEvBody(e.target.value)}
                rows={3}
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              />
            </label>
            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setEvidenceModalOpen(false)}
                className={CH_BTN_SECONDARY}
              >
                Abbrechen
              </button>
              <button type="button" disabled={busy} onClick={() => void onSubmitEvidence()} className={CH_BTN_PRIMARY}>
                Speichern
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );

  return (
    <GovernanceWorkspaceLayout
      eyebrow="Enterprise · Governance"
      title="Unified Controls"
      status="active"
      headerDescription={
        <span className="text-slate-700">
          Obligationen und Maßnahmen normenübergreifend bündeln (EU AI Act, ISO 42001, ISO 27001/27701,
          NIS2/KRITIS). Export und Pagination für Mandanten mit großem Register.
        </span>
      }
      breadcrumbs={[
        { label: "Tenant", href: "/tenant/compliance-overview" },
        { label: "Governance", href: "/tenant/governance/overview" },
        { label: "Controls" },
      ]}
      tabs={[{ id: "dash", label: "Übersicht", content: dashboard }]}
      activeTabId="dash"
      onTabChange={() => {}}
    />
  );
}
