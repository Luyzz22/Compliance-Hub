"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { GovernanceWorkspaceLayout } from "@/components/governance/GovernanceWorkspaceLayout";
import { StatusBadge } from "@/components/governance/StatusBadge";
import {
  fetchAutomationSummary,
  fetchEscalations,
  fetchReminders,
  postAcknowledgeEscalation,
  postAutomationRun,
  type RemediationAutomationRunResponseDto,
  type RemediationAutomationSummaryDto,
  type RemediationEscalationItemDto,
  type RemediationReminderItemDto,
} from "@/lib/remediationAutomationApi";
import { CH_BTN_PRIMARY, CH_BTN_SECONDARY, CH_CARD, CH_SECTION_LABEL } from "@/lib/boardLayout";

interface Props {
  tenantId: string;
}

function sevTone(s: string): "success" | "warning" | "neutral" {
  if (s === "severe" || s === "management_followup") return "warning";
  if (s === "overdue") return "neutral";
  return "neutral";
}

export function RemediationAutomationWorkspaceClient({ tenantId }: Props) {
  const [summary, setSummary] = useState<RemediationAutomationSummaryDto | null>(null);
  const [escalations, setEscalations] = useState<RemediationEscalationItemDto[]>([]);
  const [reminders, setReminders] = useState<RemediationReminderItemDto[]>([]);
  const [lastRun, setLastRun] = useState<RemediationAutomationRunResponseDto | null>(null);
  const [sevFilter, setSevFilter] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [ackingActionId, setAckingActionId] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setErr(null);
    try {
      const [s, e, r] = await Promise.all([
        fetchAutomationSummary(tenantId),
        fetchEscalations(tenantId, {
          status: "open",
          limit: 150,
          severity: sevFilter || undefined,
        }),
        fetchReminders(tenantId, { status: "open", limit: 150 }),
      ]);
      setSummary(s);
      setEscalations(e.items);
      setReminders(r.items);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Laden fehlgeschlagen");
    }
  }, [tenantId, sevFilter]);

  useEffect(() => {
    void reload();
  }, [reload]);

  useEffect(() => {
    if (!successMsg) return;
    const t = window.setTimeout(() => setSuccessMsg(null), 4000);
    return () => window.clearTimeout(t);
  }, [successMsg]);

  async function onRun() {
    setBusy(true);
    setErr(null);
    setSuccessMsg(null);
    try {
      const res = await postAutomationRun(tenantId);
      setLastRun(res);
      await reload();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Lauf fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  }

  async function onAcknowledgeAction(actionId: string) {
    setAckingActionId(actionId);
    setErr(null);
    setSuccessMsg(null);
    try {
      const r = await postAcknowledgeEscalation(tenantId, actionId);
      if (r.acknowledged === 0) {
        setSuccessMsg("Keine offenen Eskalationen mehr (bereits quittiert oder entfallen).");
      } else {
        setSuccessMsg(
          r.acknowledged === 1
            ? "Eine Eskalation wurde quittiert."
            : `${r.acknowledged} Eskalationen wurden quittiert.`,
        );
      }
      await reload();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Quittieren fehlgeschlagen");
    } finally {
      setAckingActionId(null);
    }
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <GovernanceWorkspaceLayout
        title="Automation & Eskalation"
        eyebrow="Governance"
        status="live"
        headerDescription={
          <div className="flex flex-wrap items-center gap-3 text-sm text-slate-600">
            <StatusBadge status="rule_engine" tone="neutral" />
            <span>
              Regelbasiert, mandant <span className="font-mono text-xs">{tenantId}</span>
            </span>
            <Link
              href="/tenant/governance/remediation"
              className="font-semibold text-[var(--sbs-navy-mid)] no-underline hover:underline"
            >
              → Maßnahmenregister
            </Link>
          </div>
        }
        breadcrumbs={[
          { label: "Tenant", href: "/tenant/compliance-overview" },
          { label: "Governance", href: "/tenant/governance/overview" },
          { label: "Remediation", href: "/tenant/governance/remediation" },
          { label: "Automation", href: "/tenant/governance/remediation/automation" },
        ]}
      >
        {err ? (
          <p className="text-sm text-rose-800" role="alert">
            {err}
          </p>
        ) : null}
        {successMsg ? (
          <p className="text-sm text-emerald-900" role="status">
            {successMsg}
          </p>
        ) : null}

        <section className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <article className={`${CH_CARD} border-slate-200/80`}>
            <p className={CH_SECTION_LABEL}>Überfällige Maßnahmen (gesamt)</p>
            <p className="mt-2 text-3xl font-semibold tabular-nums text-rose-800">
              {summary?.overdue_actions ?? "—"}
            </p>
          </article>
          <article className={`${CH_CARD} border-slate-200/80`}>
            <p className={CH_SECTION_LABEL}>Severe Eskalationen (offen)</p>
            <p className="mt-2 text-3xl font-semibold tabular-nums text-amber-900">
              {summary?.severe_escalations_open ?? "—"}
            </p>
          </article>
          <article className={`${CH_CARD} border-slate-200/80`}>
            <p className={CH_SECTION_LABEL}>Reminders heute</p>
            <p className="mt-2 text-3xl font-semibold tabular-nums text-slate-900">
              {summary?.reminders_due_today ?? "—"}
            </p>
          </article>
          <article className={`${CH_CARD} border-slate-200/80`}>
            <p className={CH_SECTION_LABEL}>Auto-generiert (7 Tage)</p>
            <p className="mt-1 text-xs text-slate-500">Summe Lauf-„generated_actions“</p>
            <p className="mt-1 text-3xl font-semibold tabular-nums text-[var(--sbs-navy-mid)]">
              {summary?.auto_generated_actions_7d ?? "—"}
            </p>
          </article>
        </section>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <label className="flex flex-col text-xs font-medium text-slate-600">
            Eskalations-Stärke
            <select
              className="mt-1 min-w-[10rem] rounded-lg border border-slate-300 bg-white px-2 py-2 text-sm"
              value={sevFilter}
              onChange={(e) => setSevFilter(e.target.value)}
            >
              <option value="">Alle</option>
              <option value="overdue">overdue</option>
              <option value="severe">severe</option>
              <option value="management_followup">management_followup</option>
            </select>
          </label>
          <button type="button" className={CH_BTN_SECONDARY} onClick={() => void reload()}>
            Aktualisieren
          </button>
          <button type="button" className={CH_BTN_PRIMARY} onClick={() => void onRun()} disabled={busy}>
            {busy ? "Lauf…" : "Automation ausführen"}
          </button>
        </div>

        {lastRun ? (
          <p className="mt-3 text-xs text-slate-600">
            Letzter Lauf: {lastRun.escalations_created} Eskalationen, {lastRun.generated_actions}{" "}
            generierte Maßnahmen, Regeln: {lastRun.rule_keys.join(", ")}
          </p>
        ) : null}

        <div className="mt-8 grid gap-6 lg:grid-cols-2">
          <article className={`${CH_CARD} overflow-hidden`}>
            <p className={CH_SECTION_LABEL}>Offene Eskalationen</p>
            <div className="mt-2 overflow-x-auto text-sm">
              <table className="min-w-full divide-y divide-slate-200 text-left">
                <thead className="bg-slate-50/90 text-xs font-semibold text-slate-500">
                  <tr>
                    <th className="px-2 py-2">Maßnahme</th>
                    <th className="px-2 py-2">Severity</th>
                    <th className="px-2 py-2">Grund</th>
                    <th className="px-2 py-2">Erfasst</th>
                    <th className="px-2 py-2 w-[1%] whitespace-nowrap">Aktion</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {escalations.length === 0 ? (
                    <tr>
                      <td className="px-2 py-4 text-slate-600" colSpan={5}>
                        Keine offenen Eskalationen in dieser Filterung.
                      </td>
                    </tr>
                  ) : (
                    escalations.map((x) => (
                      <tr key={x.id}>
                        <td className="px-2 py-2 max-w-[14rem]">
                          <p className="font-medium text-slate-900 line-clamp-2" title={x.action_title || undefined}>
                            {x.action_title || "—"}
                          </p>
                          <p className="mt-0.5 font-mono text-[0.7rem] text-slate-500">{x.action_id}</p>
                          {x.detail ? (
                            <p className="mt-1 text-xs text-slate-500 line-clamp-2" title={x.detail}>
                              {x.detail}
                            </p>
                          ) : null}
                        </td>
                        <td className="px-2 py-2">
                          <StatusBadge status={x.severity} tone={sevTone(x.severity)} />
                        </td>
                        <td className="px-2 py-2 text-slate-700">{x.reason_code}</td>
                        <td className="px-2 py-2 text-slate-600">
                          {new Date(x.created_at_utc).toLocaleString("de-DE")}
                        </td>
                        <td className="px-2 py-2">
                          <button
                            type="button"
                            className={CH_BTN_SECONDARY}
                            disabled={busy || ackingActionId === x.action_id}
                            aria-label={`Eskalationen zu Maßnahme ${x.action_id} quittieren`}
                            onClick={() => void onAcknowledgeAction(x.action_id)}
                          >
                            {ackingActionId === x.action_id ? "…" : "Quittieren"}
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </article>

          <article className={`${CH_CARD} overflow-hidden`}>
            <p className={CH_SECTION_LABEL}>Aktive Reminder</p>
            <div className="mt-2 overflow-x-auto text-sm">
              <table className="min-w-full divide-y divide-slate-200 text-left">
                <thead className="bg-slate-50/90 text-xs font-semibold text-slate-500">
                  <tr>
                    <th className="px-2 py-2">Fällig (UTC)</th>
                    <th className="px-2 py-2">Maßnahme</th>
                    <th className="px-2 py-2">Kind</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {reminders.length === 0 ? (
                    <tr>
                      <td className="px-2 py-4 text-slate-600" colSpan={3}>
                        Keine offenen Reminder.
                      </td>
                    </tr>
                  ) : (
                    reminders.map((m) => (
                      <tr key={m.id}>
                        <td className="px-2 py-2 text-slate-800">
                          {new Date(m.remind_at_utc).toLocaleString("de-DE")}
                        </td>
                        <td className="px-2 py-2 max-w-[14rem]">
                          <p className="font-medium text-slate-900 line-clamp-2">{m.action_title || "—"}</p>
                          <p className="mt-0.5 font-mono text-[0.7rem] text-slate-500">{m.action_id}</p>
                        </td>
                        <td className="px-2 py-2">{m.kind}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </article>
        </div>

        <p className="mt-6 text-xs text-slate-500">
          „Quittieren“ schließt alle noch offenen Eskalationen zu genau dieser Maßnahme ab (pro
          Mandant, auditierbar über{" "}
          <code className="rounded bg-slate-100 px-1">remediation_escalation.ack</code>).
        </p>
      </GovernanceWorkspaceLayout>
    </div>
  );
}
