/**
 * NIS2/KRITIS-Wizard — API-Schicht (Stub).
 *
 * TODO: Auf FastAPI-Router unter z. B. /api/v1/nis2/wizard/... verdrahten (Tenant-Header wie
 * aiActSelfAssessmentApi). Bis dahin: deterministische Mocks für UI-Entwicklung.
 */
import type { GovernanceAuditEventRow } from "@/lib/aiActSelfAssessmentModels";
import { formatGovernanceDateTime } from "@/lib/formatGovernanceDate";
import type { Nis2WizardSession } from "@/lib/nis2WizardModels";

export type Nis2ApiOk<T> = { ok: true; data: T };
export type Nis2ApiErr = { ok: false; status: number; message: string };
export type Nis2ApiResult<T> = Nis2ApiOk<T> | Nis2ApiErr;

/** TODO: GET /api/v1/nis2/wizard/sessions/{session_id} */
export async function fetchNis2WizardSession(
  _tenantId: string,
  sessionId: string,
): Promise<Nis2ApiResult<Nis2WizardSession>> {
  await Promise.resolve();
  return {
    ok: true,
    data: {
      session_id: sessionId,
      tenant_id: _tenantId,
      status: "in_progress",
      schema_version: "2026.04",
      started_at: new Date().toISOString(),
      completed_at: null,
    },
  };
}

/** TODO: GET /api/v1/nis2/wizard/sessions/{session_id}/answers */
export async function fetchNis2WizardAnswers(
  _tenantId: string,
  _sessionId: string,
): Promise<Nis2ApiResult<Record<string, unknown>>> {
  await Promise.resolve();
  return { ok: true, data: {} };
}

/** TODO: PUT /api/v1/nis2/wizard/sessions/{session_id}/answers/{question_key} */
export async function saveNis2WizardAnswer(
  _tenantId: string,
  _sessionId: string,
  _questionKey: string,
  _value: unknown,
): Promise<Nis2ApiResult<unknown>> {
  await Promise.resolve();
  return { ok: true, data: {} };
}

/** TODO: POST /api/v1/nis2/wizard/sessions/{session_id}/complete */
export async function completeNis2WizardSession(
  _tenantId: string,
  _sessionId: string,
): Promise<Nis2ApiResult<Nis2WizardSession>> {
  await Promise.resolve();
  return {
    ok: true,
    data: {
      session_id: _sessionId,
      tenant_id: _tenantId,
      status: "completed",
      schema_version: "2026.04",
      started_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
    },
  };
}

/** TODO: POST /api/v1/nis2/wizard/sessions/{session_id}/export */
export async function exportNis2WizardSession(
  _tenantId: string,
  _sessionId: string,
): Promise<Nis2ApiResult<{ download_url?: string }>> {
  await Promise.resolve();
  return { ok: true, data: { download_url: undefined } };
}

export interface Nis2WizardAuditEventStub {
  event_type: string;
  user?: string;
  timestamp: string;
  details?: string;
}

/** TODO: GET /api/v1/audit/nis2-wizard/sessions/{session_id}/events */
export async function fetchNis2WizardAuditEvents(
  _tenantId: string,
  _sessionId: string,
): Promise<Nis2ApiResult<Nis2WizardAuditEventStub[]>> {
  await Promise.resolve();
  return {
    ok: true,
    data: [
      {
        event_type: "session_initialized",
        user: "workspace",
        timestamp: new Date().toISOString(),
        details: "Stub: Wizard-Session angelegt (Block 3).",
      },
    ],
  };
}

export function mapNis2AuditStubsToRows(events: Nis2WizardAuditEventStub[]): GovernanceAuditEventRow[] {
  return events.map((e, i) => ({
    rowKey: `${e.timestamp}-${i}`,
    eventType: e.event_type,
    actor: e.user ?? "—",
    whenIso: e.timestamp,
    whenDisplay: formatGovernanceDateTime(e.timestamp),
    details: e.details ?? "—",
  }));
}
