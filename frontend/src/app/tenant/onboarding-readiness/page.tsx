import Link from "next/link";

import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import { fetchEnterpriseOnboardingReadiness } from "@/lib/api";
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
    </div>
  );
}
