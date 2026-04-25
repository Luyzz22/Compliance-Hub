"use client";

import { useCallback, useEffect, useState } from "react";

import { GovernanceWorkspaceLayout } from "@/components/governance/GovernanceWorkspaceLayout";
import { StatusBadge } from "@/components/governance/StatusBadge";
import { CH_CARD, CH_SECTION_LABEL, CH_BTN_PRIMARY, CH_BTN_SECONDARY } from "@/lib/boardLayout";
import {
  fetchNotificationDeliveries,
  fetchWorkflowDashboard,
  fetchWorkflowEvents,
  fetchWorkflowNotifications,
  fetchWorkflowTaskDetail,
  fetchWorkflowTasks,
  patchWorkflowTask,
  postTestNotification,
  postWorkflowRun,
  WorkflowApiError,
  type GovernanceWorkflowDashboardDto,
  type WorkflowEventDto,
  type WorkflowNotificationDeliveryDto,
  type WorkflowNotificationDto,
  type WorkflowRunListItem,
  type WorkflowTaskListItemDto,
  type WorkflowTaskDetailDto,
} from "@/lib/governanceWorkflowApi";
import {
  getEventsCountFromRunSummary,
  isAllowedStatusTransition,
  isWorkflowTaskStatus,
  assertWorkflowTaskStatus,
  WORKFLOW_SOURCE_TYPE_VALUES,
  WORKFLOW_TASK_STATUS_VALUES,
  type WorkflowTaskStatus,
} from "@/lib/governanceWorkflowTypes";

interface Props {
  tenantId: string;
}

function priorityTone(
  p: string
): "success" | "warning" | "neutral" {
  if (p === "critical" || p === "high") return "warning";
  if (p === "medium") return "neutral";
  return "success";
}

function runDurationLabel(startedAt: string, completedAt: string | null): string {
  if (!completedAt) return "…";
  const ms = new Date(completedAt).getTime() - new Date(startedAt).getTime();
  if (!Number.isFinite(ms) || ms < 0) return "—";
  if (ms < 2000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

function taskActionErrorText(e: unknown): string {
  if (e instanceof WorkflowApiError && e.status === 422) {
    return "Ungültiger Status – bitte Seite aktualisieren oder Workflow-Status prüfen.";
  }
  if (e instanceof Error) {
    return e.message;
  }
  return "Aktualisierung fehlgeschlagen";
}

function pickDefaultTargetStatus(current: string): WorkflowTaskStatus {
  if (!isWorkflowTaskStatus(current)) {
    return "open";
  }
  const next = WORKFLOW_TASK_STATUS_VALUES.find(
    (s) => s !== current && isAllowedStatusTransition(current, s)
  );
  return next ?? current;
}

export function GovernanceWorkflowsWorkspaceClient({ tenantId }: Props) {
  const [activeTab, setActiveTab] = useState<"main" | "events" | "notif">("main");
  const [dash, setDash] = useState<GovernanceWorkflowDashboardDto | null>(null);
  const [tasks, setTasks] = useState<WorkflowTaskListItemDto[]>([]);
  const [events, setEvents] = useState<WorkflowEventDto[]>([]);
  const [notifs, setNotifs] = useState<WorkflowNotificationDto[]>([]);
  const [deliv, setDeliv] = useState<WorkflowNotificationDeliveryDto[]>([]);
  const [notice, setNotice] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [fStatus, setFStatus] = useState("");
  const [fSource, setFSource] = useState("");
  const [fAsg, setFAsg] = useState("");
  const [fSev, setFSev] = useState("");
  const [fFw, setFFw] = useState("");
  const [selTask, setSelTask] = useState<WorkflowTaskDetailDto | null>(null);
  const [selId, setSelId] = useState<string | null>(null);
  const [targetStatus, setTargetStatus] = useState<WorkflowTaskStatus>("open");

  const recentRuns: WorkflowRunListItem[] = dash?.recent_runs ?? [];
  const lastRun = recentRuns[0];
  const previousRun = recentRuns[1];
  const lastRunEventCount = getEventsCountFromRunSummary(lastRun?.summary);
  const previousRunEventCount = getEventsCountFromRunSummary(previousRun?.summary);
  const eventTrend =
    lastRun && previousRun
      ? lastRunEventCount - previousRunEventCount
      : null;

  const loadAll = useCallback(async () => {
    try {
      const dash1 = await fetchWorkflowDashboard(tenantId);
      setDash(dash1);
      const [t, ev, n, dlv] = await Promise.all([
        fetchWorkflowTasks(tenantId, {
          status: fStatus || undefined,
          source_type: fSource || undefined,
          assignee: fAsg || undefined,
          severity: fSev || undefined,
          framework: fFw || undefined,
        }),
        fetchWorkflowEvents(tenantId),
        fetchWorkflowNotifications(tenantId),
        fetchNotificationDeliveries(tenantId),
      ]);
      setTasks(t);
      setEvents(ev);
      setNotifs(n);
      setDeliv(dlv);
    } catch (e) {
      setNotice({
        kind: "error",
        text: e instanceof Error ? e.message : "Laden fehlgeschlagen",
      });
    }
  }, [tenantId, fStatus, fSource, fAsg, fSev, fFw]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  useEffect(() => {
    if (!selId) {
      setSelTask(null);
      return;
    }
    void (async () => {
      try {
        setNotice(null);
        const d = await fetchWorkflowTaskDetail(tenantId, selId);
        setSelTask(d);
        setTargetStatus(pickDefaultTargetStatus(d.status));
      } catch (e) {
        setNotice({
          kind: "error",
          text: e instanceof Error ? e.message : "Detail fehlgeschlagen",
        });
      }
    })();
  }, [selId, tenantId]);

  async function onRun() {
    setBusy(true);
    setNotice(null);
    try {
      const r = await postWorkflowRun(tenantId);
      setNotice({
        kind: "success",
        text: `Regel-Sync abgeschlossen: ${r.events_written} Ereignis(se), ${r.tasks_materialized} Task(s) materialisiert.`,
      });
      await loadAll();
    } catch (e) {
      setNotice({ kind: "error", text: e instanceof Error ? e.message : "Lauf fehlgeschlagen" });
    } finally {
      setBusy(false);
    }
  }

  async function onTestNotif() {
    setBusy(true);
    setNotice(null);
    try {
      await postTestNotification(tenantId);
      setNotice({ kind: "success", text: "Test-Benachrichtigung erstellt (Audit-Trail)." });
      await loadAll();
    } catch (e) {
      setNotice({ kind: "error", text: e instanceof Error ? e.message : "Test fehlgeschlagen" });
    } finally {
      setBusy(false);
    }
  }

  async function applyStatusChange() {
    if (!selTask) return;
    try {
      assertWorkflowTaskStatus(targetStatus);
    } catch (e) {
      setNotice({
        kind: "error",
        text: e instanceof Error ? e.message : "Ungültiger Status",
      });
      return;
    }
    if (!isAllowedStatusTransition(selTask.status, targetStatus)) {
      setNotice({
        kind: "error",
        text: "Dieser Statuswechsel ist in der UI nicht vorgesehen (abgeschlossene Tasks werden nicht erneut geöffnet).",
      });
      return;
    }
    setBusy(true);
    setNotice(null);
    try {
      await patchWorkflowTask(tenantId, selTask.id, { status: targetStatus });
      const d = await fetchWorkflowTaskDetail(tenantId, selTask.id);
      setSelTask(d);
      setTargetStatus(pickDefaultTargetStatus(d.status));
      setNotice({ kind: "success", text: "Status aktualisiert." });
      await loadAll();
    } catch (e) {
      setNotice({ kind: "error", text: taskActionErrorText(e) });
    } finally {
      setBusy(false);
    }
  }

  async function onUnassign() {
    if (!selTask) return;
    setBusy(true);
    setNotice(null);
    try {
      await patchWorkflowTask(tenantId, selTask.id, { assignee_user_id: null });
      const d = await fetchWorkflowTaskDetail(tenantId, selTask.id);
      setSelTask(d);
      setNotice({ kind: "success", text: "Zuweisung entfernt." });
      await loadAll();
    } catch (e) {
      setNotice({ kind: "error", text: taskActionErrorText(e) });
    } finally {
      setBusy(false);
    }
  }

  const mainTab = (
    <div className="space-y-6">
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <article className={`${CH_CARD} border-slate-200/80`}>
          <p className={CH_SECTION_LABEL}>Offene Tasks</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-slate-900">
            {dash?.kpis.open_tasks ?? "—"}
          </p>
        </article>
        <article className={`${CH_CARD} border-amber-900/20`}>
          <p className={CH_SECTION_LABEL}>Überfällig</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-amber-900">
            {dash?.kpis.overdue_tasks ?? "—"}
          </p>
        </article>
        <article className={`${CH_CARD} border-rose-200/80`}>
          <p className={CH_SECTION_LABEL}>Eskaliert (Task/Level)</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-rose-800">
            {dash?.kpis.escalated_tasks ?? "—"}
          </p>
        </article>
        <article className={`${CH_CARD} border-slate-200/80`}>
          <p className={CH_SECTION_LABEL}>Notifications (queue)</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-[var(--sbs-navy-mid)]">
            {dash?.kpis.notifications_queued ?? "—"}
          </p>
        </article>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <article className={`${CH_CARD} border-indigo-200/80`}>
          <p className={CH_SECTION_LABEL}>Events im letzten Run (Summary)</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-indigo-900">
            {lastRun != null ? lastRunEventCount : "—"}
          </p>
          {lastRun == null ? (
            <p className="mt-1 text-xs text-slate-500">Noch kein Run in der Historie.</p>
          ) : (
            <p className="mt-1 text-xs text-slate-600">
              {eventTrend === null ? (
                "Kein vorheriger Run zum Vergleich"
              ) : eventTrend > 0 ? (
                <span>
                  Gegenüber vorherigem Run:{" "}
                  <span className="font-medium text-rose-700">+{eventTrend} Events</span>
                </span>
              ) : eventTrend < 0 ? (
                <span>
                  Gegenüber vorherigem Run:{" "}
                  <span className="font-medium text-emerald-800">{eventTrend} Events</span>
                </span>
              ) : (
                "Gleich wie im vorherigen Run"
              )}
            </p>
          )}
        </article>
        <article className={`${CH_CARD} sm:col-span-1 border-slate-200/80`}>
          <p className={CH_SECTION_LABEL}>Regel-Sync (Kurzinfo)</p>
          <p className="mt-1 text-sm text-slate-700">
            <span className="font-mono text-xs">
              {dash?.rule_bundle_version ?? "—"}
            </span>
            <span className="mx-1.5 text-slate-300">|</span>
            Ereignisse 24h: {dash?.kpis.workflow_events_24h ?? "—"}
          </p>
          <p className="mt-2 text-xs text-slate-500">
            <code>events_written</code> = während <code>run_sync</code> erzeugte Workflow-Events; siehe
            Run-Tabelle.
          </p>
        </article>
      </section>

      <div className="flex flex-wrap gap-2">
        <button type="button" className={CH_BTN_PRIMARY} onClick={() => void onRun()} disabled={busy}>
          {busy ? "…" : "Regel-Sync ausführen"}
        </button>
        <button
          type="button"
          className={CH_BTN_SECONDARY}
          onClick={() => void loadAll()}
          disabled={busy}
        >
          Aktualisieren
        </button>
      </div>

      <div className="flex flex-wrap items-end gap-3 border-t border-slate-100 pt-4">
        <label className="text-xs font-medium text-slate-600">
          Status
          <select
            className="mt-1 block rounded border border-slate-300 bg-white px-2 py-1.5 text-sm"
            value={fStatus}
            onChange={(e) => setFStatus(e.target.value)}
          >
            <option value="">(alle)</option>
            {WORKFLOW_TASK_STATUS_VALUES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs font-medium text-slate-600">
          Quelle
          <select
            className="mt-1 block min-w-[12rem] rounded border border-slate-300 bg-white px-2 py-1.5 text-sm"
            value={fSource}
            onChange={(e) => setFSource(e.target.value)}
          >
            <option value="">(alle / frei)</option>
            {WORKFLOW_SOURCE_TYPE_VALUES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs font-medium text-slate-600">
          Bearbeiter
          <input
            className="mt-1 block min-w-[8rem] rounded border border-slate-300 px-2 py-1.5 text-sm"
            value={fAsg}
            onChange={(e) => setFAsg(e.target.value)}
            placeholder="owner id"
          />
        </label>
        <label className="text-xs font-medium text-slate-600">
          Priorität
          <select
            className="mt-1 block rounded border border-slate-300 bg-white px-2 py-1.5 text-sm"
            value={fSev}
            onChange={(e) => setFSev(e.target.value)}
          >
            <option value="">(alle)</option>
            <option value="critical">critical</option>
            <option value="high">high</option>
            <option value="medium">medium</option>
            <option value="low">low</option>
          </select>
        </label>
        <label className="text-xs font-medium text-slate-600">
          Framework (Teilstring)
          <input
            className="mt-1 block min-w-[6rem] rounded border border-slate-300 px-2 py-1.5 text-sm"
            value={fFw}
            onChange={(e) => setFFw(e.target.value)}
            placeholder="ISO"
          />
        </label>
      </div>

      <article className={`${CH_CARD} overflow-hidden`}>
        <p className={CH_SECTION_LABEL}>Run-Historie (letzte {recentRuns.length})</p>
        <div className="mt-2 overflow-x-auto text-sm">
          <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
            <thead className="bg-slate-50/90 text-slate-500">
              <tr>
                <th className="px-2 py-2">Start (lokal)</th>
                <th className="px-2 py-2">Dauer</th>
                <th className="px-2 py-2">neue Tasks</th>
                <th className="px-2 py-2">Events (summary)</th>
                <th className="px-2 py-2">Status / Bundle</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {recentRuns.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-2 py-3 text-slate-600">
                    Noch keine Runs. „Regel-Sync ausführen“ klicken.
                  </td>
                </tr>
              ) : (
                recentRuns.map((run) => {
                  const s = run.summary;
                  const tasksN =
                    s && typeof s.tasks_materialized === "number" ? s.tasks_materialized : "—";
                  const evN = getEventsCountFromRunSummary(s);
                  return (
                    <tr key={run.id}>
                      <td className="px-2 py-1.5 whitespace-nowrap">
                        {new Date(run.started_at_utc).toLocaleString("de-DE")}
                      </td>
                      <td className="px-2 py-1.5">
                        {runDurationLabel(run.started_at_utc, run.completed_at_utc ?? null)}
                      </td>
                      <td className="px-2 py-1.5 tabular-nums">{tasksN}</td>
                      <td className="px-2 py-1.5 tabular-nums">{evN}</td>
                      <td className="px-2 py-1.5">
                        {run.status} · <span className="font-mono"> {run.rule_bundle_version}</span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </article>

      <article className={`${CH_CARD} overflow-hidden`}>
        <p className={CH_SECTION_LABEL}>Workflow Tasks</p>
        <div className="mt-2 overflow-x-auto text-sm">
          <table className="min-w-full divide-y divide-slate-200 text-left">
            <thead className="bg-slate-50/90 text-xs font-semibold text-slate-500">
              <tr>
                <th className="px-2 py-2">Titel</th>
                <th className="px-2 py-2">Status</th>
                <th className="px-2 py-2">Quelle</th>
                <th className="px-2 py-2">Fällig</th>
                <th className="px-2 py-2 w-[1%]">Detail</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {tasks.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-2 py-4 text-slate-600">
                    Keine Tasks. Regel-Sync ausführen, wenn Quellen (Remediation, Controls, …) Daten
                    liefern.
                  </td>
                </tr>
              ) : (
                tasks.map((t) => (
                  <tr key={t.id}>
                    <td className="px-2 py-2 max-w-md">
                      <p className="font-medium line-clamp-2">{t.title}</p>
                      <p className="font-mono text-[0.7rem] text-slate-500">
                        {t.id} / {t.source_id}
                      </p>
                    </td>
                    <td className="px-2 py-2">
                      <StatusBadge status={t.status} tone="neutral" />
                      {t.is_overdue ? (
                        <span className="ml-1 text-amber-800 text-xs">(überfällig)</span>
                      ) : null}
                    </td>
                    <td className="px-2 py-2">
                      <div className="text-xs text-slate-600">{t.source_type}</div>
                      <div className="text-xs">
                        <StatusBadge
                          status={t.priority}
                          tone={priorityTone(t.priority)}
                        />
                      </div>
                    </td>
                    <td className="px-2 py-2 text-slate-700 text-xs">
                      {t.due_at_utc
                        ? new Date(t.due_at_utc).toLocaleString("de-DE")
                        : "—"}
                    </td>
                    <td className="px-2 py-2">
                      <button
                        type="button"
                        className={CH_BTN_SECONDARY}
                        onClick={() => setSelId(t.id === selId ? null : t.id)}
                      >
                        {selId === t.id ? "▲" : "▼"}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </article>

      {selId && selTask ? (
        <article className={`${CH_CARD}`}>
          <p className={CH_SECTION_LABEL}>Task-Detail</p>
          <dl className="mt-3 grid gap-2 sm:grid-cols-2 text-sm">
            <div>
              <dt className="text-xs text-slate-500">Aktueller Status</dt>
              <dd>
                <StatusBadge status={selTask.status} tone="neutral" />
              </dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Bearbeiter (assignee_user_id)</dt>
              <dd className="font-mono text-xs break-all">
                {selTask.assignee_user_id ?? "— (nicht zugewiesen)"}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Quelle (Objekt)</dt>
              <dd>
                {selTask.source_type} — <span className="font-mono text-xs">{selTask.source_id}</span>
              </dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Fällig</dt>
              <dd>
                {selTask.due_at_utc
                  ? new Date(selTask.due_at_utc).toLocaleString("de-DE")
                  : "—"}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Referenz (JSON)</dt>
              <dd className="font-mono text-xs break-all">
                {JSON.stringify(selTask.source_ref).slice(0, 200)}
                {JSON.stringify(selTask.source_ref).length > 200 ? "…" : ""}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Bemerkung (letzte)</dt>
              <dd>{selTask.last_comment || "—"}</dd>
            </div>
          </dl>
          <div className="mt-4">
            <p className="text-xs font-semibold text-slate-500 mb-1">Status-Historie</p>
            <ol className="list-decimal list-inside space-y-1 text-sm text-slate-700">
              {selTask.history.length === 0 ? (
                <li className="text-slate-500">Keine Historieneinträge.</li>
              ) : (
                selTask.history.map((h, i) => (
                  <li key={i}>
                    {new Date(h.at_utc).toLocaleString("de-DE")} · {h.from_status} → {h.to_status} ·
                    {h.actor_id}
                    {h.note ? ` — ${h.note}` : ""}
                  </li>
                ))
              )}
            </ol>
          </div>
          <div className="mt-4 space-y-3">
            <div className="flex flex-wrap items-end gap-2">
              <label className="text-xs font-medium text-slate-600">
                Neuer Status
                <select
                  className="mt-1 block min-w-[12rem] rounded border border-slate-300 bg-white px-2 py-1.5 text-sm"
                  value={targetStatus}
                  onChange={(e) => setTargetStatus(e.target.value as WorkflowTaskStatus)}
                >
                  {WORKFLOW_TASK_STATUS_VALUES.map((s) => {
                    const allowed = isAllowedStatusTransition(selTask.status, s);
                    return (
                      <option key={s} value={s} disabled={!allowed}>
                        {s}
                        {!allowed ? " (gesperrt)" : ""}
                      </option>
                    );
                  })}
                </select>
              </label>
              <button
                type="button"
                className={CH_BTN_PRIMARY}
                disabled={busy}
                onClick={() => void applyStatusChange()}
              >
                Status übernehmen
              </button>
            </div>
            {selTask.assignee_user_id ? (
              <div>
                <button
                  type="button"
                  className={CH_BTN_SECONDARY}
                  disabled={busy}
                  onClick={() => void onUnassign()}
                >
                  Zuweisung entfernen (null)
                </button>
                <p className="mt-1 text-xs text-slate-500">
                  Setzt <code>assignee_user_id</code> per JSON <code>null</code> (explizit unassigned).
                </p>
              </div>
            ) : null}
          </div>
        </article>
      ) : null}
    </div>
  );

  const eventsTab = (
    <div className="space-y-4">
      <article className={`${CH_CARD} overflow-hidden`}>
        <p className={CH_SECTION_LABEL}>Recent Workflow Events</p>
        <div className="mt-2 max-h-96 overflow-auto text-sm">
          <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
            <thead className="bg-slate-50/90 text-slate-500">
              <tr>
                <th className="px-2 py-1">Zeit (UTC)</th>
                <th className="px-2 py-1">Typ</th>
                <th className="px-2 py-1">Nachricht</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {events.map((e) => (
                <tr key={e.id}>
                  <td className="px-2 py-1.5 whitespace-nowrap">
                    {new Date(e.at_utc).toLocaleString("de-DE")}
                  </td>
                  <td className="px-2 py-1.5">{e.event_type}</td>
                  <td className="px-2 py-1.5">{e.message || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>
    </div>
  );

  const notifTab = (
    <div className="space-y-6">
      <div>
        <button
          type="button"
          className={CH_BTN_SECONDARY}
          onClick={() => void onTestNotif()}
          disabled={busy}
        >
          Test-Benachrichtigung (Audit-Trail)
        </button>
        <p className="mt-1 text-xs text-slate-500">POST /governance/workflows/notifications/test</p>
      </div>
      <article className={`${CH_CARD} overflow-hidden`}>
        <p className={CH_SECTION_LABEL}>Notifications</p>
        <div className="mt-2 max-h-64 overflow-auto text-xs">
          {notifs.length === 0 ? (
            <p className="text-slate-500">Noch keine Einträge.</p>
          ) : (
            <ul className="space-y-1">
              {notifs.map((n) => (
                <li key={n.id} className="border-b border-slate-100 py-1">
                  <span className="font-medium">{n.title}</span> · {n.status} · {n.channel} ·
                  {new Date(n.created_at_utc).toLocaleString("de-DE")}
                </li>
              ))}
            </ul>
          )}
        </div>
      </article>
      <article className={`${CH_CARD} overflow-hidden`}>
        <p className={CH_SECTION_LABEL}>Deliveries</p>
        <div className="mt-2 max-h-64 overflow-auto text-xs">
          {deliv.length === 0 ? (
            <p className="text-slate-500">Noch kein Zustellprotokoll.</p>
          ) : (
            <ul className="space-y-1">
              {deliv.map((d) => (
                <li key={d.id} className="border-b border-slate-100 py-1">
                  {d.result} — {d.channel} — {new Date(d.delivered_at_utc).toLocaleString("de-DE")}
                </li>
              ))}
            </ul>
          )}
        </div>
      </article>
    </div>
  );

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <GovernanceWorkspaceLayout
        title="Workflows & Tasks"
        eyebrow="Governance"
        status="live"
        headerDescription={
          <p className="text-sm text-slate-600">
            Mandant: <span className="font-mono text-xs">{tenantId}</span> – deterministische
            Regeln, auditierbar; externe Zustellung in Phase 2.
          </p>
        }
        breadcrumbs={[
          { label: "Tenant", href: "/tenant/compliance-overview" },
          { label: "Governance", href: "/tenant/governance/overview" },
          { label: "Workflows", href: "/tenant/governance/workflows" },
        ]}
        toast={notice}
        tabs={[
          { id: "main", label: "Übersicht", content: mainTab },
          { id: "events", label: "Ereignisse", content: eventsTab },
          { id: "notif", label: "Benachrichtigungen", content: notifTab },
        ]}
        activeTabId={activeTab}
        onTabChange={(t) => setActiveTab(t as "main" | "events" | "notif")}
      />
    </div>
  );
}
