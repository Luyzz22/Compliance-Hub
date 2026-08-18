import Link from "next/link";

import { StartNis2WizardButton } from "@/components/nis2/StartNis2WizardButton";
import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import { CH_CARD, CH_PAGE_NAV_LINK, CH_SECTION_LABEL, CH_SHELL } from "@/lib/boardLayout";
import { TENANT_NIS2_WIZARD_BASE } from "@/lib/nis2WizardRoutes";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

export default async function TenantNis2WizardIndexPage() {
  const tenantId = await getWorkspaceTenantIdServer();

  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        eyebrow="Enterprise · Block 3"
        title="NIS2 / KRITIS — Onboarding-Wizard"
        description={
          <>
            Indikative Einordnung nach NIS2 (DE, BSIG) und KRITIS-Dachgesetz — ohne
            Übergangsfrist, mit Fokus auf Geschäftsleiter-Verantwortung. Der Wizard erzeugt ein
            initiales Risiko-/Readiness-Profil und empfiehlt Control-Cluster (Stub).
          </>
        }
        breadcrumbs={[
          { label: "Tenant", href: "/tenant/compliance-overview" },
          { label: "NIS2 Wizard" },
        ]}
        actions={<StartNis2WizardButton tenantId={tenantId} />}
      />

      <section className={CH_CARD}>
        <p className={CH_SECTION_LABEL}>Start</p>
        <p className="mt-2 text-sm text-slate-600">
          Legen Sie eine neue Wizard-Session an. Die technische Persistenz folgt über die
          geplanten Endpunkte unter <code className="text-xs">nis2_wizard</code> (TODO).
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <StartNis2WizardButton tenantId={tenantId} />
          <Link href="/board/nis2-kritis" className={CH_PAGE_NAV_LINK}>
            Zum Board NIS2/KRITIS
          </Link>
        </div>
        <p className="mt-4 text-xs text-slate-500">
          Basis-URL dieser Übersicht: <span className="font-mono">{TENANT_NIS2_WIZARD_BASE}</span>
        </p>
      </section>
    </div>
  );
}
