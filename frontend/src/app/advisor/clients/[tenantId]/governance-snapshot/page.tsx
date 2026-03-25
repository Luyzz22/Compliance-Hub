import { notFound } from "next/navigation";

import { AdvisorGovernanceSnapshotView } from "@/components/advisor/AdvisorGovernanceSnapshotView";
import { featureAdvisorClientSnapshot, featureAdvisorWorkspace } from "@/lib/config";

export default async function AdvisorClientGovernanceSnapshotPage({
  params,
}: {
  params: Promise<{ tenantId: string }>;
}) {
  if (!featureAdvisorWorkspace() || !featureAdvisorClientSnapshot()) {
    notFound();
  }
  const { tenantId } = await params;
  const decoded = decodeURIComponent(tenantId);
  return <AdvisorGovernanceSnapshotView clientTenantId={decoded} />;
}
