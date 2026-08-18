import Link from "next/link";

import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import { TransparencyAssuranceWorkspace } from "@/components/tenant/TransparencyAssuranceWorkspace";
import { fetchAITransparencyAssurance } from "@/lib/api";
import { CH_BTN_SECONDARY, CH_PAGE_NAV_LINK, CH_SHELL } from "@/lib/boardLayout";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

export default async function TransparencyAssurancePage() {
  const tenantId = await getWorkspaceTenantIdServer();
  const data = await fetchAITransparencyAssurance(tenantId);

  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        eyebrow="EU AI Act · DSGVO"
        title="Transparency Assurance"
        description="Prüfbares Kontrollregister für die Transparenzpflichten je KI-System – mit Provider-/Deployer-Scope, Evidenz, Vier-Augen-Review und Wiedervorlage."
        breadcrumbs={[
          { label: "Workspace", href: "/tenant/compliance-overview" },
          { label: "EU AI Act", href: "/tenant/eu-ai-act" },
          { label: "Transparency Assurance" },
        ]}
        actions={
          <Link href="/tenant/ai-systems" className={CH_BTN_SECONDARY}>
            Zum KI-System-Register
          </Link>
        }
        below={
          <>
            <Link href="/tenant/eu-ai-act" className={CH_PAGE_NAV_LINK}>
              EU AI Act Cockpit
            </Link>
            <Link href="/tenant/audit-log" className={CH_PAGE_NAV_LINK}>
              Audit-Log prüfen
            </Link>
          </>
        }
      />

      <TransparencyAssuranceWorkspace tenantId={tenantId} initialData={data} />
    </div>
  );
}
