import React from "react";

import { AiActEvidencePageClient } from "@/components/evidence/AiActEvidencePageClient";

export default async function AiActEvidencePage({
  params,
}: {
  params: Promise<{ tenantId: string }>;
}) {
  const { tenantId: raw } = await params;
  const tenantId = decodeURIComponent(raw);
  return <AiActEvidencePageClient tenantId={tenantId} />;
}
