"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { GovernanceWorkspaceLayout } from "@/components/governance/GovernanceWorkspaceLayout";
import { HealthStatusPill } from "@/components/governance/HealthStatusPill";
import { StatusBadge } from "@/components/governance/StatusBadge";
import {
  fetchBoardReport,
  generateBoardReport,
  type BoardReportDetailDto,
  type BoardMetricDto,
} from "@/lib/boardReportingApi";
import { CH_BTN_PRIMARY, CH_CARD, CH_SECTION_LABEL } from "@/lib/boardLayout";

interface Props {
  tenantId: string;
  reportId: string;
}

function metricTone(m: BoardMetricDto) {
  if (m.traffic_light === "red") return "text-rose-800";
  if (m.traffic_light === "amber") return "text-amber-800";
  return "text-emerald-800";
}

export function BoardReportsWorkspaceClient({ tenantId, reportId }: Props) {
  const [tab, setTab] = useState<"overview" | "actions" | "trends" | "trail">("overview");
  const [report, setReport] = useState<BoardReportDetailDto | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      setReport(await fetchBoardReport(tenantId, reportId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Laden fehlgeschlagen");
    }
  }, [tenantId, reportId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function regenerateCurrentPeriod() {
    if (!report) return;
    setBusy(true);
    setError(null);
    try {
      const next = await generateBoardReport(tenantId, {
        period_key: report.period_key,
        period_type: report.period_type === "quarterly" ? "quarterly" : "monthly",
        period_start: report.period_start,
        period_end: report.period_end,
        title: report.title,
      });
      window.location.href = `/tenant/governance/board-reports/${next.id}`;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generierung fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  }

  const summaryTiles = (
    <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {(report?.summary.metrics ?? []).slice(0, 6).map((m) => (
        <article key={m.metric_key} className={`${CH_CARD} border-slate-200/80`}>
          <p className={CH_SECTION_LABEL}>{m.label}</p>
          <p className={`mt-2 text-3xl font-semibold tabular-nums ${metricTone(m)}`}>
            {m.unit === "percent" ? `${m.value}%` : m.value}
          </p>
          <p className="mt-1 text-xs text-slate-600">
            Trend: {m.trend_direction} ({m.trend_delta > 0 ? "+" : ""}
            {m.trend_delta})
          </p>
        </article>
      ))}
    </section>
  );

  const overview = (
    <div className="space-y-6">
      {error ? (
        <p className="text-sm text-rose-800" role="alert">
          {error}
        </p>
      ) : null}
      {summaryTiles}
      <article className={CH_CARD}>
        <p className={CH_SECTION_LABEL}>Top Risk Areas</p>
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-700">
          {(report?.summary.top_risk_areas ?? []).map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      </article>
      <article className={CH_CARD}>
        <p className={CH_SECTION_LABEL}>Operational Resilience</p>
        <div className="mt-3 flex items-center gap-3">
          <HealthStatusPill
            status={
              report?.summary.resilience_summary_de?.includes("HIGH")
                ? "down"
                : report?.summary.resilience_summary_de?.includes("MEDIUM")
                ? "degraded"
                : "up"
            }
            label="Resilience"
          />
          <span className="text-sm text-slate-700">{report?.summary.resilience_summary_de}</span>
        </div>
      </article>
    </div>
  );

  const actionsTab = (
    <article className={CH_CARD}>
      <p className={CH_SECTION_LABEL}>Open Board Actions</p>
      <div className="mt-3 overflow-x-auto rounded-xl border border-slate-200/80">
        <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
          <thead className="bg-slate-50/90 text-xs font-semibold uppercase text-slate-500">
            <tr>
              <th className="px-3 py-2">Action</th>
              <th className="px-3 py-2">Owner</th>
              <th className="px-3 py-2">Priority</th>
              <th className="px-3 py-2">Due</th>
              <th className="px-3 py-2">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {(report?.actions ?? []).map((a) => (
              <tr key={a.id}>
                <td className="px-3 py-2">
                  <p className="font-medium text-slate-900">{a.action_title}</p>
                  <p className="text-xs text-slate-600">{a.action_detail ?? "—"}</p>
                </td>
                <td className="px-3 py-2">{a.owner ?? "—"}</td>
                <td className="px-3 py-2">{a.priority}</td>
                <td className="px-3 py-2">{a.due_at ? new Date(a.due_at).toLocaleDateString("de-DE") : "—"}</td>
                <td className="px-3 py-2">
                  <StatusBadge status={a.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );

  const trendsTab = (
    <article className={CH_CARD}>
      <p className={CH_SECTION_LABEL}>Trend vs Previous Period</p>
      <ul className="mt-3 space-y-2 text-sm text-slate-700">
        {(report?.summary.metrics ?? []).map((m) => (
          <li key={m.metric_key} className="flex items-center justify-between rounded-lg border border-slate-100 p-3">
            <span>{m.label}</span>
            <span className={metricTone(m)}>
              {m.trend_direction} ({m.trend_delta > 0 ? "+" : ""}
              {m.trend_delta})
            </span>
          </li>
        ))}
      </ul>
    </article>
  );

  const trailTab = (
    <article className={CH_CARD}>
      <p className={CH_SECTION_LABEL}>Audit Trail</p>
      <ul className="mt-3 space-y-2 text-xs text-slate-700">
        {(report?.audit_trail ?? []).map((e, idx) => (
          <li key={`${e.created_at_utc ?? idx}-${idx}`} className="rounded-lg border border-slate-100 p-3">
            {e.created_at_utc} · {e.actor} · {e.action} · {e.outcome}
          </li>
        ))}
      </ul>
    </article>
  );

  return (
    <GovernanceWorkspaceLayout
      eyebrow="Enterprise · Management Pack"
      title={report?.title ?? "Board Report"}
      status={report?.status ?? "generated"}
      headerDescription={
        <div className="text-slate-700">
          <p>{report?.summary.headline_de ?? "Board-ready Snapshot aus Controls, Audits und Operations."}</p>
          <p className="mt-1 text-xs text-slate-500">
            Zeitraum {report?.period_key} · {report?.period_type} · erstellt{" "}
            {report?.generated_at_utc ? new Date(report.generated_at_utc).toLocaleString("de-DE") : "—"}
          </p>
        </div>
      }
      headerActions={
        <div className="flex gap-2">
          <button type="button" onClick={() => void regenerateCurrentPeriod()} className={CH_BTN_PRIMARY} disabled={busy}>
            {busy ? "Generiert..." : "Periode neu berechnen"}
          </button>
          <Link href="/tenant/governance/board-reports" className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 no-underline">
            Report-Liste
          </Link>
        </div>
      }
      breadcrumbs={[
        { label: "Tenant", href: "/tenant/compliance-overview" },
        { label: "Governance", href: "/tenant/governance/overview" },
        { label: "Board Reports", href: "/tenant/governance/board-reports" },
        { label: "Detail" },
      ]}
      tabs={[
        { id: "overview", label: "Overview", content: overview },
        { id: "actions", label: "Actions", content: actionsTab },
        { id: "trends", label: "Trends", content: trendsTab },
        { id: "trail", label: "Audit Trail", content: trailTab },
      ]}
      activeTabId={tab}
      onTabChange={(id) => setTab(id as typeof tab)}
    />
  );
}
