import Link from "next/link";

import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import {
  fetchConnectorRuntimeStatus,
  fetchConnectorSyncRunHistory,
  fetchEnterpriseConnectorCandidates,
  fetchEnterpriseIntegrationBlueprints,
  fetchEnterpriseOnboardingReadiness,
  triggerConnectorRetrySync,
} from "@/lib/api";
import {
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_SECTION_LABEL,
  CH_SHELL,
} from "@/lib/boardLayout";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

type PageProps = {
  searchParams?: Promise<{ retry_connector_sync?: string; sync_run_id?: string }>;
};

export default async function TenantOnboardingReadinessPage({ searchParams }: PageProps) {
  const tenantId = await getWorkspaceTenantIdServer();
  const qp = (await searchParams) ?? {};
  const retryResult =
    qp.retry_connector_sync === "1"
      ? await triggerConnectorRetrySync(tenantId, qp.sync_run_id ?? null)
      : null;
  const data = await fetchEnterpriseOnboardingReadiness(tenantId);
  const blueprint = await fetchEnterpriseIntegrationBlueprints(tenantId, false);
  const candidates = await fetchEnterpriseConnectorCandidates(tenantId, false);
  const connectorRuntime = await fetchConnectorRuntimeStatus(tenantId);
  const connectorSyncHistory = await fetchConnectorSyncRunHistory(tenantId, 15);

  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        eyebrow="Enterprise"
        title="Onboarding Readiness"
        description="Kompakter Onboarding-Status für Tenant-Struktur, SSO, Identity-Mapping und Integrationsbereitschaft."
        actions={
          <Link href="/tenant/control-center" className={`${CH_BTN_SECONDARY} text-sm`}>
            Zum Control Center
          </Link>
        }
      />

      <section className="grid gap-4 md:grid-cols-4">
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Blocker</p>
          <p className="mt-2 text-3xl font-semibold text-rose-700">{data.blockers.length}</p>
        </article>
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>SSO</p>
          <p className="mt-2 text-lg font-semibold text-slate-900">
            {data.sso_readiness.provider_type} · {data.sso_readiness.onboarding_status}
          </p>
        </article>
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Role Mapping</p>
          <p className="mt-2 text-lg font-semibold text-slate-900">
            {data.sso_readiness.role_mapping_status}
          </p>
        </article>
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Integrationen</p>
          <p className="mt-2 text-3xl font-semibold text-slate-900">{data.integration_readiness.length}</p>
        </article>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Tenant-Struktur</p>
          <ul className="mt-3 space-y-2 text-sm text-slate-700">
            {data.tenant_structure.map((e) => (
              <li key={e.entity_code} className="rounded border border-slate-200 px-3 py-2">
                <p className="font-medium">{e.name}</p>
                <p className="text-xs text-slate-500">
                  {e.entity_code} · {e.entity_type}
                  {e.parent_entity_code ? ` · parent=${e.parent_entity_code}` : ""}
                </p>
              </li>
            ))}
            {data.tenant_structure.length === 0 ? (
              <li className="text-xs text-slate-500">Noch keine Einheiten modelliert.</li>
            ) : null}
          </ul>
        </article>

        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Integrationsbereitschaft</p>
          <ul className="mt-3 space-y-2 text-sm text-slate-700">
            {data.integration_readiness.map((i) => (
              <li key={`${i.target_type}-${i.owner ?? "na"}`} className="rounded border border-slate-200 px-3 py-2">
                <p className="font-medium">
                  {i.target_type} · {i.readiness_status}
                </p>
                <p className="text-xs text-slate-500">
                  Owner: {i.owner ?? "—"} · Blocker: {i.blocker ?? "—"}
                </p>
              </li>
            ))}
            {data.integration_readiness.length === 0 ? (
              <li className="text-xs text-slate-500">Keine Integrationsziele hinterlegt.</li>
            ) : null}
          </ul>
        </article>
      </section>

      <section className={CH_CARD}>
        <p className={CH_SECTION_LABEL}>Integration Blueprint Reuse</p>
        <p className="mt-2 text-sm text-slate-700">
          Aktuelle Integrations-Posture: <span className="font-semibold">{blueprint.readiness_status}</span>
          {" · "}Top-Kandidaten: {blueprint.top_enterprise_integration_candidates.length}
        </p>
        <ul className="mt-3 space-y-2 text-xs text-slate-700">
          {blueprint.top_enterprise_integration_candidates.slice(0, 3).map((item) => (
            <li key={item.blueprint_id} className="rounded border border-slate-200 px-3 py-2">
              {item.source_system_type} ({item.score}/100) - {item.recommendation_de}
            </li>
          ))}
          {blueprint.top_enterprise_integration_candidates.length === 0 ? (
            <li className="text-xs text-slate-500">Noch keine priorisierten Integrationskandidaten.</li>
          ) : null}
        </ul>
      </section>

      <section className={CH_CARD}>
        <p className={CH_SECTION_LABEL}>Connector Candidate Scoring</p>
        <p className="mt-2 text-sm text-slate-700">
          Empfohlener Erst-Connector:{" "}
          <span className="font-semibold">
            {candidates.candidate_rows[0]?.connector_type ?? "—"}
          </span>
          {" · "}
          Priorität: {candidates.candidate_rows[0]?.recommended_priority ?? "—"}
        </p>
        <ul className="mt-3 space-y-2 text-xs text-slate-700">
          {candidates.candidate_rows.slice(0, 3).map((row) => (
            <li key={`cand-${row.connector_type}`} className="rounded border border-slate-200 px-3 py-2">
              {row.connector_type}: Score {row.score_total}/100 · Readiness {row.readiness_score}
              {" · "}Blocker {row.blocker_score} · {row.rationale_summary_de}
            </li>
          ))}
        </ul>
        <p className="mt-3 text-xs text-slate-600">
          Live-Connector-Status: {connectorRuntime.connector_instance.source_system_type} · Instanz{" "}
          {connectorRuntime.connector_instance.sync_status}
          {" · "}letzter abgeschlossener Lauf: {connectorRuntime.health.last_terminal_sync ?? "—"}
          {" · "}Evidence im Speicher: {connectorRuntime.health.evidence_record_count}
        </p>
        {connectorRuntime.health.has_material_connector_issue &&
        connectorRuntime.health.material_issue_summary_de ? (
          <p className="mt-2 rounded border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
            {connectorRuntime.health.material_issue_summary_de}
          </p>
        ) : null}
        {connectorRuntime.last_sync_result?.operator_next_step_de ? (
          <p className="mt-2 text-xs text-slate-700">
            <span className="font-semibold">Nächster Schritt:</span>{" "}
            {connectorRuntime.last_sync_result.operator_next_step_de}
          </p>
        ) : null}
        {connectorRuntime.last_sync_result &&
        connectorRuntime.last_sync_result.retry_recommended ? (
          <div className="mt-2 flex flex-wrap gap-2 text-xs">
            <Link
              className="rounded border border-cyan-600 bg-cyan-50 px-3 py-1 font-semibold text-cyan-900"
              href={`/tenant/onboarding-readiness?retry_connector_sync=1&sync_run_id=${encodeURIComponent(
                connectorRuntime.last_sync_result.sync_run_id,
              )}`}
            >
              Sicheren Retry (letzter fehlgeschlagener/teilweiser Lauf)
            </Link>
            <span className="text-slate-500">
              Idempotent: bereits verarbeitete externe IDs werden aktualisiert, nicht dupliziert.
            </span>
          </div>
        ) : null}
        {retryResult ? (
          <p className="mt-2 rounded border border-cyan-200 bg-cyan-50 px-3 py-2 text-xs text-cyan-950">
            Retry abgeschlossen: {retryResult.sync_result.sync_status} · normalisiert{" "}
            {retryResult.sync_result.records_normalized} (Dauer {retryResult.sync_result.duration_ms ?? "—"} ms).
          </p>
        ) : null}
        <div className="mt-4 overflow-x-auto">
          <p className={CH_SECTION_LABEL}>Sync-Verlauf (kompakt)</p>
          <table className="mt-2 w-full min-w-[520px] border-collapse text-left text-xs text-slate-700">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="py-1 pr-2 font-medium">Start</th>
                <th className="py-1 pr-2 font-medium">Status</th>
                <th className="py-1 pr-2 font-medium">Kategorie</th>
                <th className="py-1 pr-2 font-medium">Norm./Empf.</th>
                <th className="py-1 pr-2 font-medium">ms</th>
                <th className="py-1 font-medium">Retry</th>
              </tr>
            </thead>
            <tbody>
              {connectorSyncHistory.runs.map((run) => (
                <tr key={run.sync_run_id} className="border-b border-slate-100">
                  <td className="py-1 pr-2 whitespace-nowrap">
                    {new Date(run.started_at_utc).toLocaleString("de-DE")}
                  </td>
                  <td className="py-1 pr-2 font-medium">{run.sync_status}</td>
                  <td className="py-1 pr-2">{run.failure_category ?? "—"}</td>
                  <td className="py-1 pr-2">
                    {run.records_normalized}/{run.records_received}
                  </td>
                  <td className="py-1 pr-2">{run.duration_ms ?? "—"}</td>
                  <td className="py-1">
                    {run.retry_recommended ? (
                      <Link
                        className="text-cyan-700 underline"
                        href={`/tenant/onboarding-readiness?retry_connector_sync=1&sync_run_id=${encodeURIComponent(run.sync_run_id)}`}
                      >
                        Retry
                      </Link>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {connectorSyncHistory.runs.length === 0 ? (
            <p className="mt-2 text-xs text-slate-500">Noch keine Sync-Läufe protokolliert.</p>
          ) : null}
        </div>
      </section>
    </div>
  );
}
