import { notFound } from "next/navigation";

/** Detail-Run: UI-Shell in SelfAssessmentWorkspaceClient (GovernanceWorkspaceLayout + Panels). */
import { SelfAssessmentWorkspaceClient } from "@/components/ai-act/SelfAssessmentWorkspaceClient";
import {
  getSelfAssessmentAnswers,
  getSelfAssessmentAuditEvents,
  getSelfAssessmentClassification,
  getSelfAssessmentSession,
} from "@/lib/aiActSelfAssessmentApi";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

interface PageProps {
  params: Promise<{ sessionId: string }>;
}

export default async function TenantSelfAssessmentSessionPage({ params }: PageProps) {
  const { sessionId: rawId } = await params;
  const sessionId = decodeURIComponent(rawId);
  const tenantId = await getWorkspaceTenantIdServer();

  const sessionRes = await getSelfAssessmentSession(tenantId, sessionId);
  if (!sessionRes.ok && sessionRes.status === 404) {
    notFound();
  }
  if (!sessionRes.ok || !sessionRes.data) {
    return (
      <div className="mx-auto max-w-3xl rounded-2xl border border-rose-200 bg-rose-50/80 p-6 shadow-sm">
        <h1 className="text-lg font-semibold text-slate-900">Self-Assessment</h1>
        <p className="mt-2 text-sm text-rose-900" role="alert">
          {!sessionRes.ok
            ? `Sitzung konnte nicht geladen werden (${sessionRes.status}): ${sessionRes.message}`
            : "Sitzung konnte nicht geladen werden: leere Antwort."}
        </p>
      </div>
    );
  }

  const session = sessionRes.data;
  const completed = session.status === "completed";

  const [answersRes, auditRes, classRes] = await Promise.all([
    getSelfAssessmentAnswers(tenantId, sessionId),
    getSelfAssessmentAuditEvents(tenantId, sessionId),
    completed
      ? getSelfAssessmentClassification(tenantId, sessionId)
      : Promise.resolve({ ok: true as const, data: null }),
  ]);

  const initialAnswers = answersRes.ok ? answersRes.data : {};
  const initialAudit = auditRes.ok ? auditRes.data : [];
  const initialClassification = classRes.ok ? classRes.data : null;

  return (
    <SelfAssessmentWorkspaceClient
      tenantId={tenantId}
      sessionId={sessionId}
      initialSession={session}
      initialAnswers={initialAnswers}
      initialAudit={initialAudit}
      initialClassification={initialClassification}
      initialAnswersError={
        answersRes.ok ? null : `${answersRes.status}: ${answersRes.message}`
      }
      initialAuditError={auditRes.ok ? null : `${auditRes.status}: ${auditRes.message}`}
      initialClassificationError={
        completed && classRes && !classRes.ok
          ? `${classRes.status}: ${classRes.message}`
          : null
      }
    />
  );
}
