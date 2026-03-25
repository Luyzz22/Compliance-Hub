import { notFound } from "next/navigation";
import React from "react";

import { AiComplianceBoardReportClient } from "@/app/board/ai-compliance-report/AiComplianceBoardReportClient";
import { featureAiComplianceBoardReport } from "@/lib/config";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

export default async function AiComplianceBoardReportPage() {
  if (!featureAiComplianceBoardReport()) {
    notFound();
  }
  const tenantId = await getWorkspaceTenantIdServer();
  return <AiComplianceBoardReportClient tenantId={tenantId} />;
}
