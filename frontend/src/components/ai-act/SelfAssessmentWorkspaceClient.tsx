"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { AiActSelfAssessmentQuestionnairePanel } from "@/components/ai-act/AiActSelfAssessmentQuestionnairePanel";
import { AuditTrailPanel } from "@/components/governance/AuditTrailPanel";
import { ClassificationPanel } from "@/components/governance/ClassificationPanel";
import { GovernanceWorkspaceLayout } from "@/components/governance/GovernanceWorkspaceLayout";
import { StatusBadge } from "@/components/governance/StatusBadge";
import {
  completeSelfAssessment,
  exportSelfAssessment,
  getSelfAssessmentAuditEvents,
  getSelfAssessmentClassification,
  getSelfAssessmentSession,
  patchSelfAssessmentSession,
  putSelfAssessmentAnswer,
  resolveExportDownloadUrl,
  type ExportSelfAssessmentResult,
  type SelfAssessmentAuditEvent,
  type SelfAssessmentClassification,
  type SelfAssessmentSessionDetail,
} from "@/lib/aiActSelfAssessmentApi";
import {
  auditEventToRow,
  toClassificationViewModel,
} from "@/lib/aiActSelfAssessmentModels";
import { TENANT_AI_ACT_SELF_ASSESSMENTS_PATH } from "@/lib/aiActSelfAssessmentRoutes";
import { CH_BTN_SECONDARY } from "@/lib/boardLayout";
import { formatGovernanceDateTime } from "@/lib/formatGovernanceDate";

type TabKey = "questionnaire" | "classification" | "audit";

export interface SelfAssessmentWorkspaceClientProps {
  tenantId: string;
  sessionId: string;
  initialSession: SelfAssessmentSessionDetail;
  initialAnswers: Record<string, unknown>;
  initialAudit: SelfAssessmentAuditEvent[];
  initialClassification: SelfAssessmentClassification | null;
  initialAnswersError?: string | null;
  initialAuditError?: string | null;
  initialClassificationError?: string | null;
}

export function SelfAssessmentWorkspaceClient({
  tenantId,
  sessionId,
  initialSession,
  initialAnswers,
  initialAudit,
  initialClassification,
  initialAnswersError,
  initialAuditError,
  initialClassificationError,
}: SelfAssessmentWorkspaceClientProps) {
  const [tab, setTab] = useState<TabKey>("questionnaire");
  const [session, setSession] = useState(initialSession);
  const [answers, setAnswers] = useState(initialAnswers);
  const [audit, setAudit] = useState<SelfAssessmentAuditEvent[]>(initialAudit);
  const [classification, setClassification] = useState<SelfAssessmentClassification | null>(
    initialClassification,
  );

  const [toast, setToast] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [inlineError, setInlineError] = useState<string | null>(null);

  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [savedAt, setSavedAt] = useState<string | null>(null);

  const [actionBusy, setActionBusy] = useState<"review" | "complete" | "export" | null>(null);

  const timers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  const latestByKey = useRef<Record<string, unknown>>({});
  const inflightSaves = useRef<Promise<void>[]>([]);

  const readOnly = session.status === "completed";

  const classificationVm = useMemo(
    () => toClassificationViewModel(classification),
    [classification],
  );

  const auditRows = useMemo(
    () =>
      audit.map((e, i) =>
        auditEventToRow(e, i, (iso) => formatGovernanceDateTime(iso)),
      ),
    [audit],
  );

  function trackInflightSave(p: Promise<void>): void {
    inflightSaves.current.push(p);
    void p.finally(() => {
      inflightSaves.current = inflightSaves.current.filter((x) => x !== p);
    });
  }

  useEffect(() => {
    setSession(initialSession);
  }, [initialSession]);

  useEffect(() => {
    setAnswers(initialAnswers);
  }, [initialAnswers]);

  useEffect(() => {
    setAudit(initialAudit);
  }, [initialAudit]);

  useEffect(() => {
    setClassification(initialClassification);
  }, [initialClassification]);

  const ownerLabel = useMemo(() => {
    return session.owner ?? session.created_by ?? "—";
  }, [session]);

  const showToast = useCallback((kind: "success" | "error", text: string) => {
    setToast({ kind, text });
    window.setTimeout(() => setToast(null), 6000);
  }, []);

  const scheduleSave = useCallback(
    (questionKey: string, value: unknown) => {
      if (readOnly) {
        return;
      }
      latestByKey.current[questionKey] = value;
      const prev = timers.current[questionKey];
      if (prev) {
        clearTimeout(prev);
      }
      setSaveState("saving");
      setInlineError(null);
      timers.current[questionKey] = setTimeout(() => {
        delete timers.current[questionKey];
        const p = (async () => {
          const res = await putSelfAssessmentAnswer(tenantId, sessionId, questionKey, value);
          if (!res.ok) {
            setSaveState("error");
            setInlineError(`${res.status}: ${res.message}`);
            showToast("error", `Speichern fehlgeschlagen (${res.status})`);
            return;
          }
          setSaveState("saved");
          setSavedAt(new Date().toISOString());
        })();
        trackInflightSave(p);
      }, 450);
    },
    [readOnly, sessionId, showToast, tenantId],
  );

  const drainInflightSaves = useCallback(async (): Promise<void> => {
    for (let i = 0; i < 25; i++) {
      const batch = inflightSaves.current.slice();
      if (batch.length === 0) {
        return;
      }
      await Promise.all(batch);
    }
  }, []);

  const flushPendingAutosaves = useCallback(async (): Promise<
    { ok: true } | { ok: false; status: number; message: string }
  > => {
    await drainInflightSaves();
    const debouncedKeys = Object.keys(timers.current);
    for (const key of debouncedKeys) {
      const tid = timers.current[key];
      if (tid) {
        clearTimeout(tid);
      }
      delete timers.current[key];
    }
    await drainInflightSaves();
    for (const key of debouncedKeys) {
      const value = latestByKey.current[key];
      const res = await putSelfAssessmentAnswer(tenantId, sessionId, key, value);
      if (!res.ok) {
        return { ok: false, status: res.status, message: res.message };
      }
      setSaveState("saved");
      setSavedAt(new Date().toISOString());
    }
    await drainInflightSaves();
    return { ok: true };
  }, [drainInflightSaves, sessionId, tenantId]);

  useEffect(() => {
    return () => {
      for (const t of Object.values(timers.current)) {
        clearTimeout(t);
      }
    };
  }, []);

  const refreshSessionAndClassification = useCallback(async () => {
    const s = await getSelfAssessmentSession(tenantId, sessionId);
    if (s.ok && s.data) {
      setSession(s.data);
    }
    if (s.ok && s.data?.status === "completed") {
      const c = await getSelfAssessmentClassification(tenantId, sessionId);
      if (c.ok) {
        setClassification(c.data);
      } else {
        showToast("error", `Klassifikation: ${c.status} ${c.message}`);
      }
    }
  }, [sessionId, showToast, tenantId]);

  const refreshAudit = useCallback(async () => {
    const r = await getSelfAssessmentAuditEvents(tenantId, sessionId);
    if (r.ok) {
      setAudit(r.data);
    }
  }, [sessionId, tenantId]);

  async function onSetInReview() {
    setInlineError(null);
    setActionBusy("review");
    const flush = await flushPendingAutosaves();
    if (!flush.ok) {
      setActionBusy(null);
      setInlineError(`${flush.status}: ${flush.message}`);
      showToast("error", flush.message);
      setSaveState("error");
      return;
    }
    const res = await patchSelfAssessmentSession(tenantId, sessionId, { status: "in_review" });
    setActionBusy(null);
    if (!res.ok) {
      setInlineError(`${res.status}: ${res.message}`);
      showToast("error", res.message);
      return;
    }
    if (res.data) {
      setSession(res.data);
    }
    showToast("success", "Status auf „In Review“ gesetzt.");
    await refreshAudit();
  }

  async function onComplete() {
    setInlineError(null);
    setActionBusy("complete");
    const flush = await flushPendingAutosaves();
    if (!flush.ok) {
      setActionBusy(null);
      setInlineError(`${flush.status}: ${flush.message}`);
      showToast(
        "error",
        `Antworten konnten vor dem Abschluss nicht gespeichert werden: ${flush.message}`,
      );
      setSaveState("error");
      return;
    }
    const res = await completeSelfAssessment(tenantId, sessionId);
    setActionBusy(null);
    if (!res.ok) {
      setInlineError(`${res.status}: ${res.message}`);
      showToast("error", res.message);
      return;
    }
    showToast("success", "Run abgeschlossen.");
    await refreshSessionAndClassification();
    await refreshAudit();
    setTab("classification");
  }

  async function onExport() {
    setInlineError(null);
    setActionBusy("export");
    const res = await exportSelfAssessment(tenantId, sessionId);
    setActionBusy(null);
    if (!res.ok) {
      setInlineError(`${res.status}: ${res.message}`);
      showToast("error", res.message);
      return;
    }
    const url = resolveExportDownloadUrl(res.data as ExportSelfAssessmentResult);
    if (!url) {
      showToast("error", "Export-Antwort enthält keinen Download-Link.");
      return;
    }
    window.open(url, "_blank", "noopener,noreferrer");
    showToast("success", "Export gestartet.");
    await refreshAudit();
  }

  function setAnswerField(key: string, value: unknown) {
    setAnswers((prev) => ({ ...prev, [key]: value }));
    scheduleSave(key, value);
  }

  const sessionShort =
    sessionId.length > 14 ? `${sessionId.slice(0, 8)}…${sessionId.slice(-4)}` : sessionId;

  const headerDescription = (
    <div className="space-y-2">
      <p className="font-mono text-sm text-slate-600">
        Session <span className="text-slate-900">{sessionShort}</span>
      </p>
      <p className="text-base text-slate-600">
        <StatusBadge status={String(session.status)} />
        <span className="mx-2 text-slate-300" aria-hidden>
          ·
        </span>
        KI-System:{" "}
        <span className="font-medium text-slate-800">
          {session.ai_system_name ?? session.ai_system_id ?? "—"}
        </span>
      </p>
    </div>
  );

  const metadataSection = (
    <dl className="grid gap-4 text-sm text-slate-700 sm:grid-cols-2">
      <div>
        <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Owner</dt>
        <dd className="mt-1 font-semibold text-slate-900">{ownerLabel}</dd>
      </div>
      <div>
        <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Schema-Version</dt>
        <dd className="mt-1 font-semibold text-slate-900">{session.schema_version ?? "—"}</dd>
      </div>
      <div>
        <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Gestartet</dt>
        <dd className="mt-1 font-semibold text-slate-900">
          {formatGovernanceDateTime(session.started_at)}
        </dd>
      </div>
      <div>
        <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Abgeschlossen</dt>
        <dd className="mt-1 font-semibold text-slate-900">
          {formatGovernanceDateTime(session.completed_at)}
        </dd>
      </div>
    </dl>
  );

  const tabs = useMemo(
    () => [
      {
        id: "questionnaire" as const,
        label: "Fragebogen",
        content: (
          <AiActSelfAssessmentQuestionnairePanel
            readOnly={readOnly}
            answers={answers}
            saveState={saveState}
            savedAt={savedAt}
            initialAnswersError={initialAnswersError ?? undefined}
            onAnswerChange={setAnswerField}
          />
        ),
      },
      {
        id: "classification" as const,
        label: "Klassifikation",
        content: (
          <ClassificationPanel
            runCompleted={session.status === "completed"}
            classificationError={initialClassificationError}
            model={classificationVm}
          />
        ),
      },
      {
        id: "audit" as const,
        label: "Audit-Trail",
        content: (
          <AuditTrailPanel
            rows={auditRows}
            initialLoadError={initialAuditError ?? undefined}
            onRefresh={() => void refreshAudit()}
          />
        ),
      },
    ],
    [
      answers,
      auditRows,
      classificationVm,
      initialAnswersError,
      initialAuditError,
      initialClassificationError,
      readOnly,
      refreshAudit,
      saveState,
      savedAt,
      session.status,
    ],
  );

  return (
    <GovernanceWorkspaceLayout
      title="Self-Assessment Run"
      eyebrow="Enterprise · EU AI Act"
      status={String(session.status)}
      headerDescription={headerDescription}
      breadcrumbs={[
        { label: "Tenant", href: "/tenant/compliance-overview" },
        { label: "Self-Assessments", href: TENANT_AI_ACT_SELF_ASSESSMENTS_PATH },
        { label: sessionShort },
      ]}
      headerActions={
        <Link href={TENANT_AI_ACT_SELF_ASSESSMENTS_PATH} className={CH_BTN_SECONDARY}>
          Zur Übersicht
        </Link>
      }
      toast={toast}
      metadataSection={metadataSection}
      actionError={inlineError}
      onStatusChange={onSetInReview}
      onComplete={onComplete}
      onExport={onExport}
      statusChangeDisabled={readOnly || session.status === "in_review"}
      completeDisabled={readOnly}
      exportDisabled={false}
      busyAction={actionBusy}
      tabs={tabs}
      activeTabId={tab}
      onTabChange={(id) => setTab(id as TabKey)}
      tablistAriaLabel="Self-Assessment Bereiche"
    />
  );
}
