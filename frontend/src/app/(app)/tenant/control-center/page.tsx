import Link from "next/link";

import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import { PreparationPackPreview } from "@/components/tenant/PreparationPackPreview";
import {
  fetchAuthorityAuditPreparationPack,
  fetchConnectorRuntimeStatus,
  fetchEnterpriseConnectorCandidates,
  fetchEnterpriseControlCenter,
  fetchEnterpriseIntegrationBlueprints,
  triggerConnectorManualSync,
  triggerConnectorRetrySync,
  type ControlCenterSeverityDto,
  type PreparationPackFocusDto,
} from "@/lib/api";
import {
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_SECTION_LABEL,
  CH_SHELL,
} from "@/lib/boardLayout";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

function severityClass(sev: ControlCenterSeverityDto): string {
  if (sev === "critical") return "border-rose-300 bg-rose-50 text-rose-800";
  if (sev === "warning") return "border-amber-300 bg-amber-50 text-amber-900";
  return "border-slate-300 bg-slate-50 text-slate-700";
}

type PageProps = {
  searchParams?: Promise<{
    generate_pack?: string;
    focus?: string;
    trigger_connector_sync?: string;
    retry_connector_sync?: string;
  }>;
};

export default async function TenantControlCenterPage({ searchParams }: PageProps) {
  const tenantId = await getWorkspaceTenantIdServer();
  const qp = (await searchParams) ?? {};
  const shouldGeneratePack = qp.generate_pack === "1";
  const shouldTriggerConnectorSync = qp.trigger_connector_sync === "1";
  const shouldRetryConnectorSync = qp.retry_connector_sync === "1";
  const focus =
    qp.focus === "audit" || qp.focus === "authority" || qp.focus === "mixed"
      ? (qp.focus as PreparationPackFocusDto)
      : "mixed";
  const syncResult = shouldTriggerConnectorSync ? await triggerConnectorManualSync(tenantId) : null;
  const retryResult = shouldRetryConnectorSync ? await triggerConnectorRetrySync(tenantId) : null;
  const data = await fetchEnterpriseControlCenter(tenantId, true);
  const blueprint = await fetchEnterpriseIntegrationBlueprints(tenantId, false);
  const candidates = await fetchEnterpriseConnectorCandidates(tenantId, false);
  const connectorRuntime = await fetchConnectorRuntimeStatus(tenantId);
  const prepPack = shouldGeneratePack
    ? await fetchAuthorityAuditPreparationPack(tenantId, focus)
    : null;

  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        eyebrow="Enterprise"
        title="Enterprise Control Center"
        description="Kompakter operativer Steuerungsblick auf kritische Governance-Signale, Fristen und Readiness-Blocker."
        actions={
          <div className="flex gap-2">
            <Link href="/tenant/compliance-overview" className={`${CH_BTN_SECONDARY} text-sm`}>
              Zur Compliance-Übersicht
            </Link>
            <Link href="/tenant/onboarding-readiness" className={`${CH_BTN_SECONDARY} text-sm`}>
              Onboarding Readiness
            </Link>
            <Link
              href={`/tenant/control-center?generate_pack=1&focus=${focus}`}
              className={`${CH_BTN_SECONDARY} text-sm`}
            >
              Preparation Pack erstellen
            </Link>
            <Link
              href="/tenant/control-center?trigger_connector_sync=1"
              className={`${CH_BTN_SECONDARY} text-sm`}
            >
              Connector Sync ausführen
            </Link>
            <Link
              href="/tenant/control-center?retry_connector_sync=1"
              className={`${CH_BTN_SECONDARY} text-sm`}
            >
              Connector Retry
            </Link>
          </div>
        }
      />

      <section className="grid gap-4 md:grid-cols-4">
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Kritisch</p>
          <p className="mt-2 text-3xl font-semibold text-rose-700">{data.summary_counts.critical}</p>
        </article>
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Warnung</p>
          <p className="mt-2 text-3xl font-semibold text-amber-700">{data.summary_counts.warning}</p>
        </article>
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Info</p>
          <p className="mt-2 text-3xl font-semibold text-slate-800">{data.summary_counts.info}</p>
        </article>
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Offene Punkte</p>
          <p className="mt-2 text-3xl font-semibold text-slate-900">{data.summary_counts.total_open}</p>
        </article>
      </section>

      <section className={CH_CARD}>
        <p className={CH_SECTION_LABEL}>Top-urgent</p>
        <ul className="mt-3 space-y-2 text-sm">
          {data.top_urgent_items.map((item) => (
            <li key={`${item.source_type}:${item.source_id}:${item.title}`} className="rounded-lg border border-slate-200 p-3">
              <div className="flex items-center justify-between gap-2">
                <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${severityClass(item.severity)}`}>
                  {item.severity}
                </span>
                <span className="text-xs text-slate-500">
                  {item.due_at ? new Date(item.due_at).toLocaleString("de-DE") : "ohne Frist"}
                </span>
              </div>
              <p className="mt-2 font-medium text-slate-900">{item.title}</p>
              <p className="mt-1 text-xs text-slate-600">{item.summary_de}</p>
              <Link className="mt-2 inline-block text-xs font-semibold text-cyan-700 underline" href={item.action_href}>
                {item.action_label}
              </Link>
            </li>
          ))}
          {data.top_urgent_items.length === 0 ? (
            <li className="text-sm text-slate-500">Keine akuten Punkte.</li>
          ) : null}
        </ul>
      </section>

      <section className={CH_CARD}>
        <div className="mb-2 flex items-center justify-between gap-2">
          <p className={CH_SECTION_LABEL}>First Live Connector Skeleton</p>
          <span className="text-xs text-slate-500">
            {connectorRuntime.connector_instance.source_system_type} ·{" "}
            {connectorRuntime.connector_instance.connection_status}
          </span>
        </div>
        <div className="rounded border border-slate-200 p-3 text-xs text-slate-700">
          {connectorRuntime.health.has_material_connector_issue &&
          connectorRuntime.health.material_issue_summary_de ? (
            <p className="mb-2 rounded border border-amber-200 bg-amber-50 px-2 py-1 text-amber-950">
              {connectorRuntime.health.material_issue_summary_de}
            </p>
          ) : null}
          <p>
            Instanz-Sync: <span className="font-semibold">{connectorRuntime.connector_instance.sync_status}</span>
            {" · "}Letzter Lauf (abgeschlossen):{" "}
            <span className="font-semibold">
              {connectorRuntime.health.last_terminal_sync ?? "—"}
            </span>
            {" · "}Evidence-Datensätze: {connectorRuntime.health.evidence_record_count}
          </p>
          <p className="mt-1">
            Domains:{" "}
            {connectorRuntime.connector_instance.enabled_evidence_domains.join(", ") || "—"}
          </p>
          <p className="mt-1">
            Letzter Sync:{" "}
            {connectorRuntime.connector_instance.last_sync_at
              ? new Date(connectorRuntime.connector_instance.last_sync_at).toLocaleString("de-DE")
              : "noch keiner"}
          </p>
          <p className="mt-1">Letzter Fehler: {connectorRuntime.connector_instance.last_error ?? "—"}</p>
          <p className="mt-1">
            Letztes Ergebnis: {connectorRuntime.last_sync_result?.summary_de ?? "Kein Sync-Lauf vorhanden."}
          </p>
          {connectorRuntime.last_sync_result?.failure_category ? (
            <p className="mt-1 text-amber-900">
              Fehlerkategorie:{" "}
              <span className="font-semibold">{connectorRuntime.last_sync_result.failure_category}</span>
              {" · "}
              {connectorRuntime.last_sync_result.operator_next_step_de}
            </p>
          ) : null}
          {syncResult ? (
            <p className="mt-2 rounded border border-emerald-200 bg-emerald-50 px-2 py-1 text-emerald-900">
              Manueller Sync: {syncResult.sync_result.sync_status} · normalisiert{" "}
              {syncResult.sync_result.records_normalized} / empfangen {syncResult.sync_result.records_received}.
            </p>
          ) : null}
          {retryResult ? (
            <p className="mt-2 rounded border border-cyan-200 bg-cyan-50 px-2 py-1 text-cyan-950">
              Retry ausgeführt: {retryResult.sync_result.sync_status} · Retry von{" "}
              {retryResult.sync_result.retry_of_sync_run_id ?? "—"}.
            </p>
          ) : null}
          <p className="mt-2 text-slate-600">
            Verlauf und Retry-Steuerung:{" "}
            <Link className="font-semibold text-cyan-700 underline" href="/tenant/onboarding-readiness">
              Onboarding Readiness
            </Link>
          </p>
        </div>
      </section>

      <section className={CH_CARD}>
        <div className="flex items-center justify-between gap-2">
          <p className={CH_SECTION_LABEL}>Connector Candidates</p>
          <span className="text-xs text-slate-500">
            {new Date(candidates.generated_at_utc).toLocaleString("de-DE")}
          </span>
        </div>
        <p className="mt-2 text-xs text-slate-600">
          Explainable Scoring: Readiness, Blocker, strategischer Wert und Compliance-Impact.
        </p>
        <div className="mt-3 grid gap-3 lg:grid-cols-2">
          <article className="rounded border border-slate-200 p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Top Kandidaten
            </p>
            <ul className="mt-2 space-y-2 text-xs text-slate-700">
              {candidates.top_priorities.slice(0, 4).map((row) => (
                <li key={`${row.tenant_id}-${row.connector_type}`} className="rounded border border-slate-100 px-2 py-1">
                  <p className="font-medium text-slate-900">
                    {row.connector_type} · {row.recommended_priority} · {row.score_total}/100
                  </p>
                  <p>{row.rationale_summary_de}</p>
                </li>
              ))}
            </ul>
          </article>
          <article className="rounded border border-slate-200 p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Größte Blocker
            </p>
            <ul className="mt-2 space-y-1 text-xs text-slate-700">
              {candidates.candidate_rows
                .slice()
                .sort((a, b) => b.blocker_score - a.blocker_score)
                .slice(0, 4)
                .map((row) => (
                  <li key={`${row.connector_type}-blocker`} className="rounded border border-amber-200 bg-amber-50 px-2 py-1">
                    {row.connector_type}: Blocker {row.blocker_score}/100 · {row.rationale_factors_de[1] ?? "—"}
                  </li>
                ))}
            </ul>
          </article>
        </div>
      </section>

      <section className={CH_CARD}>
        <div className="flex items-center justify-between gap-2">
          <p className={CH_SECTION_LABEL}>Integration Blueprint</p>
          <span className="text-xs text-slate-500">
            Status: {blueprint.readiness_status} · {new Date(blueprint.generated_at_utc).toLocaleString("de-DE")}
          </span>
        </div>
        <div className="mt-3 grid gap-3 lg:grid-cols-2">
          <article className="rounded border border-slate-200 p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Top geplante Connectoren
            </p>
            <ul className="mt-2 space-y-2 text-sm text-slate-700">
              {blueprint.top_enterprise_integration_candidates.slice(0, 3).map((cand) => (
                <li key={cand.blueprint_id} className="rounded border border-slate-100 px-2 py-1">
                  <p className="font-medium text-slate-900">
                    {cand.source_system_type} · {cand.score}/100
                  </p>
                  <p className="text-xs text-slate-600">{cand.recommendation_de}</p>
                </li>
              ))}
              {blueprint.top_enterprise_integration_candidates.length === 0 ? (
                <li className="text-xs text-slate-500">Noch keine Connector-Kandidaten modelliert.</li>
              ) : null}
            </ul>
          </article>
          <article className="rounded border border-slate-200 p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Fehlende Voraussetzungen und Blocker
            </p>
            <ul className="mt-2 space-y-1 text-sm text-slate-700">
              {blueprint.blockers.slice(0, 5).map((blocker) => (
                <li key={blocker} className="rounded border border-amber-200 bg-amber-50 px-2 py-1 text-xs">
                  {blocker}
                </li>
              ))}
              {blueprint.blockers.length === 0 ? (
                <li className="text-xs text-slate-500">Keine dokumentierten Blocker.</li>
              ) : null}
            </ul>
          </article>
        </div>
        <div className="mt-3 rounded border border-slate-200 p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Systeme und Evidence-Domains
          </p>
          <ul className="mt-2 space-y-1 text-xs text-slate-700">
            {blueprint.blueprint_rows.slice(0, 5).map((row) => (
              <li key={row.blueprint_id}>
                <span className="font-medium text-slate-900">{row.source_system_type}</span> ({row.integration_status})
                {" -> "}
                {row.evidence_domains.join(", ") || "keine Domains"}
              </li>
            ))}
          </ul>
        </div>
      </section>

      {prepPack ? (
        <section className={CH_CARD}>
          <div className="mb-3 flex items-center justify-between">
            <p className={CH_SECTION_LABEL}>Authority & Audit Preparation Pack</p>
            <span className="text-xs text-slate-500">
              Fokus: {prepPack.focus} · {new Date(prepPack.generated_at_utc).toLocaleString("de-DE")}
            </span>
          </div>
          <PreparationPackPreview markdown={prepPack.markdown_de} />
        </section>
      ) : null}

      <section className="grid gap-4 lg:grid-cols-2">
        {data.grouped_sections.map((group) => (
          <article key={group.section} className={CH_CARD}>
            <p className={CH_SECTION_LABEL}>{group.label_de}</p>
            <ul className="mt-3 space-y-2">
              {group.items.slice(0, 6).map((item) => (
                <li key={`${item.source_type}:${item.source_id}:${item.title}`} className="rounded border border-slate-200 px-3 py-2">
                  <p className="text-sm font-medium text-slate-900">{item.title}</p>
                  <p className="text-xs text-slate-600">{item.summary_de}</p>
                </li>
              ))}
              {group.items.length === 0 ? (
                <li className="text-xs text-slate-500">Keine offenen Punkte in diesem Bereich.</li>
              ) : null}
            </ul>
          </article>
        ))}
      </section>
    </div>
  );
}
