/** Mandanten-Workspace: EU AI Act Self-Assessment (Enterprise Shell). */
export const TENANT_AI_ACT_SELF_ASSESSMENTS_PATH = "/tenant/ai-act/self-assessments";

export function tenantAiActSelfAssessmentDetailPath(sessionId: string): string {
  return `${TENANT_AI_ACT_SELF_ASSESSMENTS_PATH}/${encodeURIComponent(sessionId)}`;
}
