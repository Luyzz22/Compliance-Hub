import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import { TenantRiskOverviewPanel } from "@/components/governance/TenantRiskOverviewPanel";
import { CH_SHELL } from "@/lib/boardLayout";
import { fetchTenantRiskOverview } from "@/lib/tenantRiskOverview";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

/**
 * Risk & Control Overview — zentrale Mandanten-Ansicht (AI Act, NIS2/KRITIS, später ISO).
 * Daten aktuell über fetchTenantRiskOverview (Stub); siehe Kommentare in lib/tenantRiskOverview.ts.
 */
export default async function TenantGovernanceOverviewPage() {
  const tenantId = await getWorkspaceTenantIdServer();
  const overview = await fetchTenantRiskOverview(tenantId);

  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        eyebrow="Enterprise · Governance"
        title="Risk & Control Overview"
        description={
          <>
            Bündelt EU AI Act (Self-Assessments & Risikostufen), NIS2/KRITIS-Exposure (Wizard) und
            Platzhalter für ISO-/Control-Fortschritt (Block 2). Indikatoren ersetzen keine
            Rechts- oder Aufsichtsbewertung.
          </>
        }
        breadcrumbs={[
          { label: "Tenant", href: "/tenant/compliance-overview" },
          { label: "Governance", href: "/tenant/governance/overview" },
          { label: "Overview" },
        ]}
      />
      <TenantRiskOverviewPanel overview={overview} />
    </div>
  );
}
