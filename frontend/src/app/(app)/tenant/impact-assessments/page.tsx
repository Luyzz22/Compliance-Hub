import Link from "next/link";

import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import { ImpactAssessmentWorkspace } from "@/components/tenant/ImpactAssessmentWorkspace";
import type { AIImpactAssessmentPortfolioResponseDto } from "@/lib/api";
import { CH_BTN_SECONDARY, CH_PAGE_NAV_LINK, CH_SHELL } from "@/lib/boardLayout";
import { serverSessionApiFetch } from "@/lib/serverBackendApi";

export default async function ImpactAssessmentsPage() {
  const response = await serverSessionApiFetch("/api/v1/impact-assessments");
  if (!response.ok) {
    throw new Error(`Impact Assessment API returned ${response.status}`);
  }
  const data = (await response.json()) as AIImpactAssessmentPortfolioResponseDto;

  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        eyebrow="DSGVO · EU AI Act"
        title="DSFA & FRIA Assessment"
        description="Versionierte Impact-Akte je KI-System: Scope, Rechte- und Freiheitsrisiken, Schutzmaßnahmen, Konsultations-Gates und unabhängige Freigabe in einem nachvollziehbaren Workflow."
        breadcrumbs={[
          { label: "Workspace", href: "/tenant/compliance-overview" },
          { label: "KI-Systeme", href: "/tenant/ai-systems" },
          { label: "DSFA & FRIA" },
        ]}
        actions={
          <Link href="/tenant/ai-systems" className={CH_BTN_SECONDARY}>
            KI-System-Register öffnen
          </Link>
        }
        below={
          <>
            <Link href="/tenant/transparency-assurance" className={CH_PAGE_NAV_LINK}>
              Transparency Assurance
            </Link>
            <Link href="/tenant/audit-log" className={CH_PAGE_NAV_LINK}>
              Audit-Log prüfen
            </Link>
          </>
        }
      />

      <ImpactAssessmentWorkspace tenantId={data.tenant_id} initialData={data} />
    </div>
  );
}
