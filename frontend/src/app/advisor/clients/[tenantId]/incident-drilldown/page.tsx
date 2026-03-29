import { AdvisorIncidentDrilldownPanel } from "@/components/advisor/AdvisorIncidentDrilldownPanel";
import { ADVISOR_ID_FROM_ENV, isAdvisorNavEnabled } from "@/lib/api";
import { featureAdvisorWorkspace, featureGovernanceMaturity } from "@/lib/config";
import { notFound } from "next/navigation";

export default async function AdvisorClientIncidentDrilldownPage({
  params,
}: {
  params: Promise<{ tenantId: string }>;
}) {
  const { tenantId: raw } = await params;
  const decoded = decodeURIComponent(raw);
  if (!isAdvisorNavEnabled() || !featureAdvisorWorkspace() || !featureGovernanceMaturity()) {
    notFound();
  }
  const advisorId = ADVISOR_ID_FROM_ENV;
  if (!advisorId) {
    notFound();
  }
  return <AdvisorIncidentDrilldownPanel advisorId={advisorId} clientTenantId={decoded} variant="full" />;
}
