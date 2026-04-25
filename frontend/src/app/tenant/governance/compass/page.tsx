import { ComplianceCompassClient } from "@/components/tenant/ComplianceCompassClient";
import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import { CH_SHELL } from "@/lib/boardLayout";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

export default async function TenantComplianceCompassPage() {
  const tenantId = await getWorkspaceTenantIdServer();

  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        eyebrow="Enterprise · Governance"
        title="Compliance Compass"
        description={
          <>
            Fusions-Index für Führung und GRC: strategische Reife, Ausführung, Sync-Kadenz und
            Lagebild – transparent pro Mandant, deterministisch berechnet; keine Rechtsberatung.
          </>
        }
        breadcrumbs={[
          { label: "Tenant", href: "/tenant/compliance-overview" },
          { label: "Governance", href: "/tenant/governance/overview" },
          { label: "Compass" },
        ]}
      />
      <ComplianceCompassClient tenantId={tenantId} />
    </div>
  );
}
