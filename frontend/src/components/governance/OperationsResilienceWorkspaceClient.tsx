"use client";

import { useCallback, useEffect, useState } from "react";

import { GovernanceWorkspaceLayout } from "@/components/governance/GovernanceWorkspaceLayout";
import { HealthStatusPill } from "@/components/governance/HealthStatusPill";
import type { HealthStatus } from "@/lib/internalHealth";
import {
  fetchOperationsKpis,
  fetchServiceHealthIncidents,
  fetchServiceHealthSnapshots,
  resolveServiceHealthIncident,
  type OperationsKpis,
  type ServiceHealthIncidentRow,
  type ServiceHealthSnapshotRow,
} from "@/lib/governanceOperationsResilience";
import { CH_CARD, CH_SECTION_LABEL } from "@/lib/boardLayout";

function asHealthStatus(s: string): HealthStatus {
  if (s === "up" || s === "degraded" || s === "down") {
    return s;
  }
  return "degraded";
}

interface Props {
  tenantId: string;
}

export function OperationsResilienceWorkspaceClient({ tenantId }: Props) {
  const [kpis, setKpis] = useState<OperationsKpis | null>(null);
  const [snapshots, setSnapshots] = useState<ServiceHealthSnapshotRow[]>([]);
  const [incidents, setIncidents] = useState<ServiceHealthIncidentRow[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busyIncidentId, setBusyIncidentId] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoadError(null);
    try {
      const [k, s, i] = await Promise.all([
        fetchOperationsKpis(tenantId),
        fetchServiceHealthSnapshots(tenantId),
        fetchServiceHealthIncidents(tenantId),
      ]);
      setKpis(k);
      setSnapshots(s);
      setIncidents(i);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "Laden fehlgeschlagen");
    }
  }, [tenantId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const openIncidents = incidents.filter((x) => x.incident_state === "open");

  async function onResolveIncident(incidentId: string) {
    setBusyIncidentId(incidentId);
    setLoadError(null);
    try {
      await resolveServiceHealthIncident(tenantId, incidentId, {
        resolved_note: "Manuell im Operations-Dashboard geschlossen.",
      });
      await reload();
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "Auflösen fehlgeschlagen");
    } finally {
      setBusyIncidentId(null);
    }
  }

  const dashboard = (
    <div className="space-y-8">
      {loadError ? (
        <p className="text-sm text-rose-800" role="alert">
          {loadError}
        </p>
      ) : null}

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <article className={`${CH_CARD} border-slate-200/80`}>
          <p className={CH_SECTION_LABEL}>Letzte Prüfung</p>
          <p className="mt-2 text-sm font-semibold text-slate-900">
            {kpis?.last_checked_at
              ? new Date(kpis.last_checked_at).toLocaleString("de-DE", {
                  dateStyle: "short",
                  timeStyle: "short",
                })
              : "—"}
          </p>
          <p className="mt-1 text-xs text-slate-600">Quelle: internal_health_poll</p>
        </article>
        <article className={`${CH_CARD} border-slate-200/80`}>
          <p className={CH_SECTION_LABEL}>Offene Incidents</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-slate-900">
            {kpis?.open_incidents ?? "—"}
          </p>
        </article>
        <article className={`${CH_CARD} border-slate-200/80`}>
          <p className={CH_SECTION_LABEL}>Services degraded</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-amber-800">
            {kpis?.degraded_services ?? "—"}
          </p>
        </article>
        <article className={`${CH_CARD} border-slate-200/80`}>
          <p className={CH_SECTION_LABEL}>Services down</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-rose-800">
            {kpis?.down_services ?? "—"}
          </p>
        </article>
      </section>

      <article className={CH_CARD}>
        <p className={CH_SECTION_LABEL}>Offene Incidents</p>
        <h2 className="mt-1 text-lg font-semibold text-slate-900">Governance &amp; Incident Readiness</h2>
        <p className="mt-2 text-sm text-slate-600">
          Automatisch aus Health-Statuswechseln erzeugt (Warning/Critical). Manuelles Abschließen
          über PATCH /api/v1/governance/operations/incidents/…/resolve (Button „Erledigt“).
        </p>
        <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200/80">
          <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
            <thead className="bg-slate-50/90 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-3 py-2">Erkannt</th>
                <th className="px-3 py-2">Service</th>
                <th className="px-3 py-2">Schwere</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Titel</th>
                <th className="px-3 py-2">Aktion</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {openIncidents.length === 0 ? (
                <tr>
                  <td className="px-3 py-4 text-slate-600" colSpan={6}>
                    Keine offenen Incidents.
                  </td>
                </tr>
              ) : (
                openIncidents.map((row) => (
                  <tr key={row.id} className="hover:bg-slate-50/80">
                    <td className="px-3 py-2 text-slate-700">
                      {new Date(row.detected_at).toLocaleString("de-DE")}
                    </td>
                    <td className="px-3 py-2 font-medium text-slate-900">{row.service_name}</td>
                    <td className="px-3 py-2 text-slate-800">{row.severity}</td>
                    <td className="px-3 py-2 text-slate-700">{row.incident_state}</td>
                    <td className="px-3 py-2 text-slate-700">{row.title}</td>
                    <td className="px-3 py-2">
                      <button
                        type="button"
                        disabled={busyIncidentId !== null}
                        onClick={() => void onResolveIncident(row.id)}
                        className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-xs font-semibold text-slate-800 shadow-sm hover:bg-slate-50 disabled:opacity-40"
                      >
                        {busyIncidentId === row.id ? "…" : "Erledigt"}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </article>

      <article className={CH_CARD}>
        <p className={CH_SECTION_LABEL}>Service Health Verlauf</p>
        <h2 className="mt-1 text-lg font-semibold text-slate-900">Snapshots (Trend / Audit)</h2>
        <p className="mt-2 text-sm text-slate-600">
          Zeilen entsprechen GET /api/v1/governance/operations/health/snapshots.
        </p>
        <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200/80">
          <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
            <thead className="bg-slate-50/90 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-3 py-2">Zeit</th>
                <th className="px-3 py-2">Service</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Quelle</th>
                <th className="px-3 py-2">poll_run_id</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {snapshots.map((row) => (
                <tr key={row.id} className="hover:bg-slate-50/80">
                  <td className="px-3 py-2 text-slate-700">
                    {new Date(row.checked_at).toLocaleString("de-DE")}
                  </td>
                  <td className="px-3 py-2 font-medium text-slate-900">{row.service_name}</td>
                  <td className="px-3 py-2">
                    <HealthStatusPill status={asHealthStatus(row.status)} label="" />
                  </td>
                  <td className="px-3 py-2 text-slate-700">{row.source}</td>
                  <td className="px-3 py-2 font-mono text-xs text-slate-600">{row.poll_run_id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>

      <p className="text-xs text-slate-500">
        Hinweis: Mandanten sehen replizierte Plattform-Health-Zeilen (MVP), damit spätere RLS und
        Dashboard-Aggregation pro tenant_id einheitlich bleiben.
      </p>
    </div>
  );

  return (
    <GovernanceWorkspaceLayout
      eyebrow="Enterprise · Governance"
      title="Betrieb &amp; Resilienz"
      status="monitoring"
      headerDescription={
        <>
          <span className="text-slate-700">
            Operational Resilience Layer — KPIs, Service-Health-Verlauf und offene
            Monitoring-Incidents (NIS2 / ISO 27001 / später ISO 42001).           Daten über GET /api/v1/governance/operations/* (NEXT_PUBLIC_API_BASE_URL / API-Key).
          </span>
        </>
      }
      breadcrumbs={[
        { label: "Tenant", href: "/tenant/compliance-overview" },
        { label: "Governance", href: "/tenant/governance/overview" },
        { label: "Operations" },
      ]}
      tabs={[{ id: "overview", label: "Übersicht", content: dashboard }]}
      activeTabId="overview"
      onTabChange={() => {}}
    />
  );
}
