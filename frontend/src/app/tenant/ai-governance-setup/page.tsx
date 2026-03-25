import { notFound } from "next/navigation";
import React from "react";

import { AiGovernanceSetupWizardClient } from "@/components/tenant/AiGovernanceSetupWizardClient";
import { fetchTenantAiGovernanceSetup } from "@/lib/api";
import { featureAiGovernanceSetupWizard } from "@/lib/config";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

export default async function AiGovernanceSetupPage() {
  if (!featureAiGovernanceSetupWizard()) {
    notFound();
  }

  const tenantId = await getWorkspaceTenantIdServer();

  let initialSetup: Awaited<ReturnType<typeof fetchTenantAiGovernanceSetup>> | null = null;
  try {
    initialSetup = await fetchTenantAiGovernanceSetup(tenantId);
  } catch {
    initialSetup = null;
  }

  return <AiGovernanceSetupWizardClient tenantId={tenantId} initialSetup={initialSetup} />;
}
