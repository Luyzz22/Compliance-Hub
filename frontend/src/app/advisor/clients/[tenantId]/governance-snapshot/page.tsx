import { Suspense } from "react";

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
  return (
    <Suspense
      fallback={
        <p className="rounded-xl border border-slate-200 bg-white px-4 py-6 text-sm text-slate-600">
          Governance-Snapshot wird geladen …
        </p>
      }
    >
      <AdvisorGovernanceSnapshotView clientTenantId={decoded} />
    </Suspense>
  );
}
