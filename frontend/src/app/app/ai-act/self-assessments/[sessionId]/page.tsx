import { redirect } from "next/navigation";

import { tenantAiActSelfAssessmentDetailPath } from "@/lib/aiActSelfAssessmentRoutes";

interface PageProps {
  params: Promise<{ sessionId: string }>;
}

/** Legacy URL unter `/app/...` → mandantenfähiger Tenant-Workspace. */
export default async function LegacySelfAssessmentSessionRedirectPage({ params }: PageProps) {
  const { sessionId: rawId } = await params;
  redirect(tenantAiActSelfAssessmentDetailPath(decodeURIComponent(rawId)));
}
