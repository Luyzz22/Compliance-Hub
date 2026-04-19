"use client";

import { useCallback, useEffect, useState } from "react";

import { GovernanceWorkspaceLayout } from "@/components/governance/GovernanceWorkspaceLayout";
import { StatusBadge } from "@/components/governance/StatusBadge";
import {
  fetchAuditControlRows,
  fetchAuditReadiness,
  fetchAuditTrail,
  type AuditReadinessControlRow,
  type AuditReadinessSummary,
  type GovernanceAuditTrailRow,
} from "@/lib/auditReadinessApi";
import { CH_CARD, CH_SECTION_LABEL } from "@/lib/boardLayout";

interface Props {
  tenantId: string;
  auditId: string;
}

export function AuditReadinessWorkspaceClient({ tenantId, auditId }: Props) {
  const [tab, setTab] = useState<"overview" | "controls" | "gaps" | "trail">("overview");
  const [summary, setSummary] = useState<AuditReadinessSummary | null>(null);
  const [controls, setControls] = useState<AuditReadinessControlRow[]>([]);
  const [trail, setTrail] = useState<GovernanceAuditTrailRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [s, c, t] = await Promise.all([
        fetchAuditReadiness(tenantId, auditId),
        fetchAuditControlRows(tenantId, auditId),
        fetchAuditTrail(tenantId, auditId),
      ]);
      setSummary(s);
      setControls(c);
      setTrail(t);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Laden fehlgeschlagen");
    }
  }, [tenantId, auditId]);

  useEffect(() => {
    void load();
  }, [load]);

  const kpi = summary ? (
    <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <article className={`${CH_CARD} border-slate-200/80`}>
        <p className={CH_SECTION_LABEL}>Readiness (gesamt)</p>
        <p className="mt-2 text-3xl font-semibold tabular-nums text-slate-900">
          {summary.overall_readiness_pct}%
        </p>
      </article>
      <article className={`${CH_CARD} border-slate-200/80`}>
        <p className={CH_SECTION_LABEL}>Controls bereit</p>
        <p className="mt-2 text-3xl font-semibold tabular-nums text-emerald-800">
          {summary.controls_ready} / {summary.controls_total}
        </p>
      </article>
      <article className={`${CH_CARD} border-slate-200/80`}>
        <p className={CH_SECTION_LABEL}>Evidence-Gaps</p>
        <p className="mt-2 text-3xl font-semibold tabular-nums text-amber-900">
          {summary.evidence_gap_count}
        </p>
      </article>
      <article className={`${CH_CARD} border-slate-200/80`}>
        <p className={CH_SECTION_LABEL}>Überfällige Reviews</p>
        <p className="mt-2 text-3xl font-semibold tabular-nums text-rose-800">
          {summary.overdue_reviews_count}
        </p>
      </article>
    </section>
  ) : null;

  const overview = (
    <div className="space-y-6">
      {error ? (
        <p className="text-sm text-rose-800" role="alert">
          {error}
        </p>
      ) : null}
      {kpi}
      {summary ? (
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Framework-Slices (deterministisch)</p>
          <div className="mt-3 overflow-x-auto rounded-xl border border-slate-200/80">
            <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
              <thead className="bg-slate-50/90 text-xs font-semibold uppercase text-slate-500">
                <tr>
                  <th className="px-3 py-2">Framework</th>
                  <th className="px-3 py-2">Im Scope</th>
                  <th className="px-3 py-2">Bereit</th>
                  <th className="px-3 py-2">Gaps</th>
                  <th className="px-3 py-2">Readiness %</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {summary.by_framework.map((f) => (
                  <tr key={f.framework_tag}>
                    <td className="px-3 py-2 font-medium">{f.framework_tag}</td>
                    <td className="px-3 py-2 tabular-nums">{f.controls_in_scope}</td>
                    <td className="px-3 py-2 tabular-nums">{f.controls_ready}</td>
                    <td className="px-3 py-2 tabular-nums">{f.evidence_gap_count}</td>
                    <td className="px-3 py-2 tabular-nums">{f.readiness_pct}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      ) : null}
    </div>
  );

  const controlsTab = (
    <div className="overflow-x-auto rounded-xl border border-slate-200/80">
      <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
        <thead className="bg-slate-50/90 text-xs font-semibold uppercase text-slate-500">
          <tr>
            <th className="px-3 py-2">Control</th>
            <th className="px-3 py-2">Tags</th>
            <th className="px-3 py-2">Status</th>
            <th className="px-3 py-2">Owner</th>
            <th className="px-3 py-2">Evidence %</th>
            <th className="px-3 py-2">Review</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {controls.map((r) => (
            <tr key={r.control_id}>
              <td className="px-3 py-2 font-medium text-slate-900">{r.title}</td>
              <td className="px-3 py-2 text-xs text-slate-600">{(r.framework_tags ?? []).join(", ")}</td>
              <td className="px-3 py-2">
                <StatusBadge status={r.status} />
              </td>
              <td className="px-3 py-2 text-slate-700">{r.owner ?? "—"}</td>
              <td className="px-3 py-2 tabular-nums">{r.evidence_completeness_pct}%</td>
              <td className="px-3 py-2 text-xs text-slate-600">
                {r.review_overdue ? (
                  <span className="font-semibold text-rose-800">überfällig</span>
                ) : r.next_review_at ? (
                  new Date(r.next_review_at).toLocaleDateString("de-DE")
                ) : (
                  "—"
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  const gapsTab = (
    <div className="overflow-x-auto rounded-xl border border-slate-200/80">
      <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
        <thead className="bg-slate-50/90 text-xs font-semibold uppercase text-slate-500">
          <tr>
            <th className="px-3 py-2">Control</th>
            <th className="px-3 py-2">Fehlender Evidence-Typ</th>
            <th className="px-3 py-2">Priorität</th>
            <th className="px-3 py-2">Empfohlene Aktion</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {(summary?.gaps ?? []).map((g, i) => (
            <tr key={`${g.control_id}-${g.missing_evidence_type_key}-${i}`}>
              <td className="px-3 py-2 font-medium">{g.control_title}</td>
              <td className="px-3 py-2 font-mono text-xs">{g.missing_evidence_type_key}</td>
              <td className="px-3 py-2 tabular-nums">P{g.priority}</td>
              <td className="px-3 py-2 text-slate-700">{g.recommended_action_de}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  const trailTab = (
    <div className="overflow-x-auto rounded-xl border border-slate-200/80">
      <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
        <thead className="bg-slate-50/90 text-xs font-semibold uppercase text-slate-500">
          <tr>
            <th className="px-3 py-2">Zeit</th>
            <th className="px-3 py-2">Actor</th>
            <th className="px-3 py-2">Aktion</th>
            <th className="px-3 py-2">Outcome</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {trail.map((r) => (
            <tr key={`${r.created_at_utc}-${r.action}`}>
              <td className="px-3 py-2 text-xs">
                {new Date(r.created_at_utc).toLocaleString("de-DE")}
              </td>
              <td className="px-3 py-2 text-xs">{r.actor}</td>
              <td className="px-3 py-2 font-mono text-[0.65rem]">{r.action}</td>
              <td className="px-3 py-2 text-xs">{r.outcome ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  const tabs = [
    { id: "overview" as const, label: "Overview", content: overview },
    { id: "controls" as const, label: "Controls", content: controlsTab },
    { id: "gaps" as const, label: "Evidence Gaps", content: gapsTab },
    { id: "trail" as const, label: "Audit Trail", content: trailTab },
  ];

  return (
    <GovernanceWorkspaceLayout
      eyebrow="Enterprise · Audit Readiness"
      title={`Audit ${auditId.slice(0, 8)}…`}
      status="active"
      headerDescription={
        <span className="text-slate-700">
          Evidence-Completeness und Review-Lage auf Basis des Unified Control Layer — regelbasiert,
          ohne KI. Daten aus dem Readiness-Endpunkt dieses Audit-Falls.
        </span>
      }
      breadcrumbs={[
        { label: "Tenant", href: "/tenant/compliance-overview" },
        { label: "Governance", href: "/tenant/governance/overview" },
        { label: "Audits", href: "/tenant/governance/audits" },
        { label: "Fall" },
      ]}
      tabs={tabs}
      activeTabId={tab}
      onTabChange={(id) => setTab(id as typeof tab)}
    />
  );
}
