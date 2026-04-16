import { notFound } from "next/navigation";

import { Nis2WizardWorkspaceClient } from "@/components/nis2/Nis2WizardWorkspaceClient";
import {
  fetchNis2WizardAnswers,
  fetchNis2WizardAuditEvents,
  fetchNis2WizardSession,
} from "@/lib/nis2WizardApi";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

interface PageProps {
  params: Promise<{ sessionId: string }>;
}

/**
 * NIS2/KRITIS-DACH Wizard (Block 3) — Detail-Run.
 * UI: GovernanceWorkspaceLayout + Stepper + Stub-API (siehe lib/nis2WizardApi.ts).
 */
export default async function TenantNis2WizardSessionPage({ params }: PageProps) {
  const { sessionId: rawId } = await params;
  const sessionId = decodeURIComponent(rawId);
  const tenantId = await getWorkspaceTenantIdServer();

  const sessionRes = await fetchNis2WizardSession(tenantId, sessionId);
  if (!sessionRes.ok && sessionRes.status === 404) {
    notFound();
  }
  if (!sessionRes.ok || !sessionRes.data) {
    return (
      <div className="mx-auto max-w-3xl rounded-2xl border border-rose-200 bg-rose-50/80 p-6 shadow-sm">
        <h1 className="text-lg font-semibold text-slate-900">NIS2 Wizard</h1>
        <p className="mt-2 text-sm text-rose-900" role="alert">
          {!sessionRes.ok
            ? `Session konnte nicht geladen werden (${sessionRes.status}): ${sessionRes.message}`
            : "Leere Antwort."}
        </p>
      </div>
    );
  }

  const [answersRes, auditRes] = await Promise.all([
    fetchNis2WizardAnswers(tenantId, sessionId),
    fetchNis2WizardAuditEvents(tenantId, sessionId),
  ]);

  return (
    <Nis2WizardWorkspaceClient
      tenantId={tenantId}
      sessionId={sessionId}
      initialSession={sessionRes.data}
      initialAnswers={answersRes.ok ? answersRes.data : {}}
      initialAudit={auditRes.ok ? auditRes.data : []}
      initialAnswersError={answersRes.ok ? null : `${answersRes.status}: ${answersRes.message}`}
      initialAuditError={auditRes.ok ? null : `${auditRes.status}: ${auditRes.message}`}
    />
  );
}
