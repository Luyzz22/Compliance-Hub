import { redirect } from "next/navigation";

import { TENANT_AI_ACT_SELF_ASSESSMENTS_PATH } from "@/lib/aiActSelfAssessmentRoutes";

/** Legacy URL: Enterprise-Workspace nutzt den Tenant-Shell-Pfad. */
export default function LegacySelfAssessmentsRedirectPage() {
  redirect(TENANT_AI_ACT_SELF_ASSESSMENTS_PATH);
}
