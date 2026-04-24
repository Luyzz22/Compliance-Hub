"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { GovernanceWorkspaceLayout } from "@/components/governance/GovernanceWorkspaceLayout";
import { HealthStatusPill } from "@/components/governance/HealthStatusPill";
import { StatusBadge } from "@/components/governance/StatusBadge";
import {
  fetchRemediationActionDetail,
  fetchRemediationActions,
  generateRemediationActions,
  postRemediationComment,
  type RemediationActionDetailDto,
  type RemediationActionListItemDto,
  type RemediationListResponseDto,
} from "@/lib/remediationActionsApi";
import { CH_BTN_PRIMARY, CH_BTN_SECONDARY, CH_CARD, CH_SECTION_LABEL } from "@/lib/boardLayout";

interface Props {
  tenantId: string;
}

function remediationTone(status: string): "success" | "warning" | "neutral" {
  if (status === "done" || status === "accepted_risk") return "success";
  if (status === "blocked" || status === "in_progress") return "warning";
  return "neutral";
}

function sourceLabel(row: RemediationActionListItemDto): string {
  const rk = row.rule_key;
  if (rk?.startsWith("evidence")) return "Audit / Evidence";
  if (rk === "weak_control") return "Control";
  if (rk === "overdue_review") return "Audit / Review";
  if (rk?.includes("incident")) return "Incident";
  if (rk?.includes("board")) return "Board Report";
  if (rk?.includes("ai_act")) return "AI Act";
  if (rk?.includes("nis2")) return "NIS2";
  switch (row.category) {
    case "audit":
      return "Audit";
    case "control":
      return "Control";
    case "incident":
      return "Incident";
    case "board":
      return "Board";
    case "ai_act":
      return "AI Act";
    case "nis2":
      return "NIS2";
    default:
      return "Manuell";
  }
}

const STATUS_LABEL_DE: Record<string, string> = {
  open: "Offen",
  in_progress: "In Bearbeitung",
  blocked: "Blockiert",
  done: "Erledigt",
  accepted_risk: "Risiko akzeptiert",
};

function linkHint(entityType: string): string {
  switch (entityType) {
    case "governance_control":
      return "Control";
    case "governance_audit_case":
      return "Audit-Fall";
    case "service_health_incident":
      return "Ops Incident";
    case "board_report":
      return "Board Report";
    case "board_report_action":
      return "Board Action";
    case "ai_system":
      return "KI-System";
    case "governance_control_review":
      return "Review";
    default:
      return entityType;
  }
}

export function RemediationWorkspaceClient({ tenantId }: Props) {
  const [pack, setPack] = useState<RemediationListResponseDto | null>(null);
  const [detail, setDetail] = useState<RemediationActionDetailDto | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [genBusy, setGenBusy] = useState(false);
  const [comment, setComment] = useState("");

  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [frameworkTag, setFrameworkTag] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [searchDebounced, setSearchDebounced] = useState("");
  const [sortKey, setSortKey] = useState<
    "updated_desc" | "due_asc" | "due_desc" | "priority_desc"
  >("updated_desc");

  useEffect(() => {
    const t = window.setTimeout(() => setSearchDebounced(searchInput.trim()), 400);
    return () => window.clearTimeout(t);
  }, [searchInput]);

  const reload = useCallback(async () => {
    setError(null);
    try {
      const next = await fetchRemediationActions(tenantId, {
        status: statusFilter || undefined,
        priority: priorityFilter || undefined,
        category: categoryFilter || undefined,
        framework_tag: frameworkTag || undefined,
        search: searchDebounced || undefined,
        sort: sortKey,
        limit: 300,
      });
      setPack(next);
      setSelectedId((sid) =>
        sid && !next.items.some((i) => i.id === sid) ? null : sid,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Laden fehlgeschlagen");
    }
  }, [
    tenantId,
    statusFilter,
    priorityFilter,
    categoryFilter,
    frameworkTag,
    searchDebounced,
    sortKey,
  ]);

  useEffect(() => {
    void reload();
  }, [reload]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    void fetchRemediationActionDetail(tenantId, selectedId).then(
      (d) => {
        if (!cancelled) setDetail(d);
      },
      (e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Detail fehlgeschlagen");
      },
    );
    return () => {
      cancelled = true;
    };
  }, [tenantId, selectedId]);

  async function onGenerate() {
    setGenBusy(true);
    setError(null);
    try {
      await generateRemediationActions(tenantId);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generierung fehlgeschlagen");
    } finally {
      setGenBusy(false);
    }
  }

  async function onPostComment() {
    if (!selectedId || !comment.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await postRemediationComment(tenantId, selectedId, comment.trim());
      setComment("");
      const d = await fetchRemediationActionDetail(tenantId, selectedId);
      setDetail(d);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Kommentar fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  }

  const summary = pack?.summary;
  const healthIncidentLinked = useMemo(() => {
    const rows = detail?.links ?? [];
    return rows.some((l) => l.entity_type === "service_health_incident");
  }, [detail]);

  const tabContent = (
    <div className="space-y-6">
      {error ? (
        <p className="text-sm text-rose-800" role="alert">
          {error}
        </p>
      ) : null}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <article className={`${CH_CARD} border-slate-200/80`}>
          <p className={CH_SECTION_LABEL}>Offen + In Arbeit</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-slate-900">
            {summary?.open_actions ?? "—"}
          </p>
        </article>
        <article className={`${CH_CARD} border-slate-200/80`}>
          <p className={CH_SECTION_LABEL}>Aktiver Backlog</p>
          <p className="mt-1 text-xs text-slate-500">inkl. blockiert</p>
          <p className="mt-1 text-3xl font-semibold tabular-nums text-slate-900">
            {summary?.backlog_actions ?? "—"}
          </p>
        </article>
        <article className={`${CH_CARD} border-slate-200/80`}>
          <p className={CH_SECTION_LABEL}>Überfällig</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-rose-800">
            {summary?.overdue_actions ?? "—"}
          </p>
        </article>
        <article className={`${CH_CARD} border-slate-200/80`}>
          <p className={CH_SECTION_LABEL}>Blockiert</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-amber-900">
            {summary?.blocked_actions ?? "—"}
          </p>
        </article>
        <article className={`${CH_CARD} border-slate-200/80`}>
          <p className={CH_SECTION_LABEL}>Fällig diese Woche</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-[var(--sbs-navy-mid)]">
            {summary?.due_this_week ?? "—"}
          </p>
        </article>
      </section>

      <div className="flex flex-wrap items-end gap-3">
        <label className="flex min-w-[12rem] flex-col text-xs font-medium text-slate-600">
          Titelsuche
          <input
            type="search"
            className="mt-1 rounded-lg border border-slate-300 bg-white px-2 py-2 text-sm"
            placeholder="z. B. Evidence, Board, Incident…"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            autoComplete="off"
          />
        </label>
        <label className="flex flex-col text-xs font-medium text-slate-600">
          Sortierung
          <select
            className="mt-1 min-w-[11rem] rounded-lg border border-slate-300 bg-white px-2 py-2 text-sm"
            value={sortKey}
            onChange={(e) => {
              const v = e.target.value;
              if (
                v === "updated_desc" ||
                v === "due_asc" ||
                v === "due_desc" ||
                v === "priority_desc"
              ) {
                setSortKey(v);
              }
            }}
          >
            <option value="updated_desc">Zuletzt geändert</option>
            <option value="due_asc">Fälligkeit (aufsteigend)</option>
            <option value="due_desc">Fälligkeit (absteigend)</option>
            <option value="priority_desc">Priorität</option>
          </select>
        </label>
        <label className="flex flex-col text-xs font-medium text-slate-600">
          Status
          <select
            className="mt-1 min-w-[10rem] rounded-lg border border-slate-300 bg-white px-2 py-2 text-sm"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">Alle</option>
            <option value="open">{STATUS_LABEL_DE.open}</option>
            <option value="in_progress">{STATUS_LABEL_DE.in_progress}</option>
            <option value="blocked">{STATUS_LABEL_DE.blocked}</option>
            <option value="done">{STATUS_LABEL_DE.done}</option>
            <option value="accepted_risk">{STATUS_LABEL_DE.accepted_risk}</option>
          </select>
        </label>
        <label className="flex flex-col text-xs font-medium text-slate-600">
          Priorität
          <select
            className="mt-1 min-w-[10rem] rounded-lg border border-slate-300 bg-white px-2 py-2 text-sm"
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
          >
            <option value="">Alle</option>
            <option value="critical">critical</option>
            <option value="high">high</option>
            <option value="medium">medium</option>
            <option value="low">low</option>
          </select>
        </label>
        <label className="flex flex-col text-xs font-medium text-slate-600">
          Quelle (Kategorie)
          <select
            className="mt-1 min-w-[12rem] rounded-lg border border-slate-300 bg-white px-2 py-2 text-sm"
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
          >
            <option value="">Alle</option>
            <option value="manual">manual</option>
            <option value="audit">audit</option>
            <option value="control">control</option>
            <option value="incident">incident</option>
            <option value="board">board</option>
            <option value="ai_act">ai_act</option>
            <option value="nis2">nis2</option>
          </select>
        </label>
        <label className="flex flex-col text-xs font-medium text-slate-600">
          Framework-Tag (Control)
          <input
            className="mt-1 min-w-[12rem] rounded-lg border border-slate-300 bg-white px-2 py-2 text-sm"
            placeholder="z. B. EU_AI_ACT"
            value={frameworkTag}
            onChange={(e) => setFrameworkTag(e.target.value)}
          />
        </label>
        <button type="button" className={CH_BTN_SECONDARY} onClick={() => void reload()}>
          Aktualisieren
        </button>
        <button type="button" className={CH_BTN_PRIMARY} onClick={() => void onGenerate()} disabled={genBusy}>
          {genBusy ? "Generiert…" : "Aus Signale generieren"}
        </button>
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <article className={`${CH_CARD} overflow-hidden`}>
            <p className={CH_SECTION_LABEL}>Maßnahmenregister</p>
            <div className="mt-3 overflow-x-auto rounded-xl border border-slate-200/80">
              <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
                <thead className="bg-slate-50/90 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-3 py-2">Titel</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2">Priorität</th>
                    <th className="px-3 py-2">Owner</th>
                    <th className="px-3 py-2">Fällig</th>
                    <th className="px-3 py-2">Quelle</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {(pack?.items ?? []).length === 0 ? (
                    <tr>
                      <td className="px-3 py-6 text-slate-600" colSpan={6}>
                        Keine Maßnahmen für die aktuelle Filterung.
                      </td>
                    </tr>
                  ) : (
                    (pack?.items ?? []).map((row) => (
                      <tr
                        key={row.id}
                        className={`cursor-pointer hover:bg-slate-50/80 ${selectedId === row.id ? "bg-slate-50" : ""}`}
                        onClick={() => setSelectedId(row.id)}
                      >
                        <td className="px-3 py-2 font-medium text-slate-900">{row.title}</td>
                        <td className="px-3 py-2">
                          <StatusBadge status={row.status} tone={remediationTone(row.status)} />
                        </td>
                        <td className="px-3 py-2 text-slate-700">{row.priority}</td>
                        <td className="px-3 py-2 text-slate-600">{row.owner ?? "—"}</td>
                        <td className="px-3 py-2 text-slate-600">
                          {row.due_at_utc ? (
                            <span className="inline-flex flex-col gap-0.5">
                              <span>{new Date(row.due_at_utc).toLocaleDateString("de-DE")}</span>
                              {row.is_overdue === true ? (
                                <span className="text-xs font-medium text-rose-700">überfällig</span>
                              ) : null}
                            </span>
                          ) : (
                            "—"
                          )}
                        </td>
                        <td className="px-3 py-2 text-slate-600">{sourceLabel(row)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </article>
        </div>

        <div className="lg:col-span-2">
          <article className={`${CH_CARD} min-h-[22rem]`}>
            <p className={CH_SECTION_LABEL}>Detail</p>
            {!selectedId ? (
              <p className="mt-4 text-sm text-slate-600">Bitte eine Zeile auswählen.</p>
            ) : !detail ? (
              <p className="mt-4 text-sm text-slate-600">Lade Detail…</p>
            ) : (
              <div className="mt-4 space-y-4 text-sm text-slate-700">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge status={detail.status} tone={remediationTone(detail.status)} />
                  <span className="text-xs text-slate-500">{detail.priority}</span>
                  {healthIncidentLinked ? (
                    <span className="inline-flex items-center gap-1 text-xs text-slate-600">
                      <HealthStatusPill status="degraded" label="Service-Health Incident" />
                    </span>
                  ) : null}
                </div>
                <h3 className="text-base font-semibold text-slate-900">{detail.title}</h3>
                {detail.description ? <p className="leading-relaxed">{detail.description}</p> : null}
                <dl className="grid gap-2 text-xs">
                  <div className="flex justify-between gap-2 border-b border-slate-100 py-1">
                    <dt className="text-slate-500">Owner</dt>
                    <dd>{detail.owner ?? "—"}</dd>
                  </div>
                  <div className="flex justify-between gap-2 border-b border-slate-100 py-1">
                    <dt className="text-slate-500">Fällig</dt>
                    <dd className="text-right">
                      {detail.due_at_utc
                        ? new Date(detail.due_at_utc).toLocaleString("de-DE")
                        : "—"}
                      {detail.is_overdue === true ? (
                        <span className="mt-0.5 block text-xs font-medium text-rose-700">
                          überfällig (aktiver Status)
                        </span>
                      ) : null}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-2 border-b border-slate-100 py-1">
                    <dt className="text-slate-500">Regel</dt>
                    <dd>{detail.rule_key ?? "—"}</dd>
                  </div>
                  {detail.deferred_note ? (
                    <div className="rounded-lg bg-amber-50/80 px-2 py-2 text-amber-950">
                      <strong className="font-semibold">Akzeptiertes Risiko:</strong>{" "}
                      {detail.deferred_note}
                    </div>
                  ) : null}
                </dl>

                <div>
                  <p className={CH_SECTION_LABEL}>Verknüpfungen</p>
                  <ul className="mt-2 space-y-1 text-xs">
                    {detail.links.map((l) => (
                      <li key={`${l.entity_type}:${l.entity_id}`}>
                        <span className="font-medium text-slate-800">{linkHint(l.entity_type)}</span>
                        {": "}
                        <code className="rounded bg-slate-100 px-1">{l.entity_id}</code>
                        {l.entity_type === "board_report" ? (
                          <>
                            {" · "}
                            <Link
                              href={`/tenant/governance/board-reports/${encodeURIComponent(l.entity_id)}`}
                              className="font-semibold text-[var(--sbs-navy-mid)] no-underline hover:underline"
                            >
                              Board Report
                            </Link>
                          </>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                </div>

                <div>
                  <p className={CH_SECTION_LABEL}>Kommentare</p>
                  <ul className="mt-2 max-h-40 space-y-2 overflow-y-auto text-xs">
                    {detail.comments.map((c) => (
                      <li key={c.id} className="rounded-lg border border-slate-100 bg-slate-50/80 px-2 py-2">
                        <p className="text-slate-800">{c.body}</p>
                        <p className="mt-1 text-slate-500">
                          {c.created_by ?? "—"} ·{" "}
                          {new Date(c.created_at_utc).toLocaleString("de-DE")}
                        </p>
                      </li>
                    ))}
                  </ul>
                  <div className="mt-3 flex gap-2">
                    <textarea
                      className="min-h-[4rem] flex-1 rounded-lg border border-slate-300 px-2 py-2 text-sm"
                      placeholder="Kommentar hinzufügen…"
                      value={comment}
                      onChange={(e) => setComment(e.target.value)}
                    />
                    <button
                      type="button"
                      className={`${CH_BTN_PRIMARY} self-end`}
                      disabled={busy || !comment.trim()}
                      onClick={() => void onPostComment()}
                    >
                      Senden
                    </button>
                  </div>
                </div>

                <div>
                  <p className={CH_SECTION_LABEL}>Status-Historie</p>
                  <ul className="mt-2 space-y-1 text-xs text-slate-600">
                    {detail.status_history.map((h) => (
                      <li key={h.id} className="rounded border border-slate-100/80 bg-white/60 px-2 py-1.5">
                        <span>
                          {(h.from_status ?? "∅")} → {h.to_status}{" "}
                          <time dateTime={h.changed_at_utc} className="text-slate-500">
                            ({new Date(h.changed_at_utc).toLocaleString("de-DE")}
                            {h.changed_by ? ` · ${h.changed_by}` : ""})
                          </time>
                        </span>
                        {h.note ? (
                          <p className="mt-1 text-slate-700">Anmerkung: {h.note}</p>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </article>
        </div>
      </div>
    </div>
  );

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <GovernanceWorkspaceLayout
        title="Remediation & Maßnahmensteuerung"
        eyebrow="Governance"
        status="live"
        headerDescription={
          <div className="flex flex-wrap items-center gap-3">
            <StatusBadge status="tenant_scoped" tone="neutral" />
            <span className="text-sm text-slate-600">
              Mandant <span className="font-mono text-xs">{tenantId}</span>
            </span>
          </div>
        }
        breadcrumbs={[
          { label: "Tenant", href: "/tenant/compliance-overview" },
          { label: "Governance", href: "/tenant/governance/overview" },
          { label: "Remediation" },
        ]}
        tabs={[{ id: "register", label: "Maßnahmenregister", content: tabContent }]}
        activeTabId="register"
        onTabChange={() => {}}
      />
    </div>
  );
}
