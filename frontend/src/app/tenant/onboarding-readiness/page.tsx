import Link from "next/link";

import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import {
  fetchEnterpriseConnectorCandidates,
  fetchEnterpriseIntegrationBlueprints,
  fetchEnterpriseOnboardingReadiness,
} from "@/lib/api";
import {
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_SECTION_LABEL,
  CH_SHELL,
} from "@/lib/boardLayout";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

export default async function TenantOnboardingReadinessPage() {
  const tenantId = await getWorkspaceTenantIdServer();
  const data = await fetchEnterpriseOnboardingReadiness(tenantId);
  const blueprint = await fetchEnterpriseIntegrationBlueprints(tenantId, false);
  const candidates = await fetchEnterpriseConnectorCandidates(tenantId, false);

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
      </section>
    </div>
  );
}
