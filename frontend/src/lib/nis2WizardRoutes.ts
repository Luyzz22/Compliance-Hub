export const TENANT_NIS2_WIZARD_BASE = "/tenant/nis2/wizard";

export function tenantNis2WizardSessionPath(sessionId: string): string {
  return `${TENANT_NIS2_WIZARD_BASE}/${encodeURIComponent(sessionId)}`;
}
