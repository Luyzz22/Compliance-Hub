"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
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
import { TENANT_AI_ACT_SELF_ASSESSMENTS_PATH } from "@/lib/aiActSelfAssessmentRoutes";
import {
  CH_BADGE,
  CH_BTN_GHOST,
  CH_BTN_PRIMARY,
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_CARD_MUTED,
  CH_SECTION_LABEL,
  CH_SHELL,
} from "@/lib/boardLayout";

type TabKey = "questionnaire" | "classification" | "audit";

const DOMAIN_OPTIONS = [
  { value: "HR", label: "HR" },
  { value: "Critical Infrastructure", label: "Kritische Infrastruktur" },
  { value: "Healthcare", label: "Gesundheitswesen" },
  { value: "Law Enforcement", label: "Strafverfolgung" },
  { value: "Other", label: "Sonstiges" },
] as const;

function asBool(v: unknown): boolean {
  if (typeof v === "boolean") {
    return v;
  }
  if (v === 1 || v === "1" || v === "true") {
    return true;
  }
  return false;
}

function asString(v: unknown, fallback: string): string {
  if (v == null) {
    return fallback;
  }
  return String(v);
}

function statusBadgeTone(status: string): string {
  switch (status) {
    case "completed":
      return "bg-emerald-100 text-emerald-900 ring-emerald-200/80";
    case "in_review":
      return "bg-amber-100 text-amber-950 ring-amber-200/80";
    default:
      return "bg-slate-100 text-slate-800 ring-slate-200/80";
  }
}

function formatTs(iso: string | null | undefined): string {
  if (!iso) {
    return "—";
  }
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) {
    return iso;
  }
  return d.toLocaleString("de-DE", { dateStyle: "short", timeStyle: "short" });
}

function formatClock(iso: string | null | undefined): string {
  if (!iso) {
    return "";
  }
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) {
    return "";
  }
  return d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
}

function auditEventType(e: SelfAssessmentAuditEvent): string {
  return String(e.event_type ?? e.type ?? "—");
}

function auditActor(e: SelfAssessmentAuditEvent): string {
  return String(e.user ?? e.actor ?? e.user_id ?? "—");
}

function auditWhen(e: SelfAssessmentAuditEvent): string {
  return String(e.timestamp ?? e.created_at ?? "—");
}

function auditDetails(e: SelfAssessmentAuditEvent): string {
  const raw = e.details ?? e.detail;
  if (raw == null) {
    return "—";
  }
  if (typeof raw === "string") {
    return raw;
  }
  try {
    return JSON.stringify(raw);
  } catch {
    return "—";
  }
}

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
  const [answers, setAnswers] = useState<Record<string, unknown>>(initialAnswers);
  const [audit, setAudit] = useState<SelfAssessmentAuditEvent[]>(initialAudit);
  const [classification, setClassification] = useState<SelfAssessmentClassification | null>(
    initialClassification,
  );

  const [toast, setToast] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [inlineError, setInlineError] = useState<string | null>(null);

  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [savedAt, setSavedAt] = useState<string | null>(null);

  const [actionBusy, setActionBusy] = useState<string | null>(null);

  const timers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  /** Letzter Wert pro Frage für sofortiges Flushen abgelaufener Debounces. */
  const latestByKey = useRef<Record<string, unknown>>({});
  /** Laufende PUT /answers (inkl. Debounce-Fires), damit Abschluss darauf warten kann. */
  const inflightSaves = useRef<Promise<void>[]>([]);

  const readOnly = session.status === "completed";

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

  /**
   * Wartet auf laufende Autosave-PUTs, bricht anstehende Debounces ab und persistiert die
   * jeweils letzten Werte — verhindert Abschluss mit veralteten Antworten oder späte PUTs
   * nach abgeschlossenem Run.
   */
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

  async function refreshSessionAndClassification() {
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
  }

  async function refreshAudit() {
    const r = await getSelfAssessmentAuditEvents(tenantId, sessionId);
    if (r.ok) {
      setAudit(r.data);
    }
  }

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
      showToast("error", `Antworten konnten vor dem Abschluss nicht gespeichert werden: ${flush.message}`);
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

  const domainValue = asString(
    answers.intended_use_domain,
    DOMAIN_OPTIONS[DOMAIN_OPTIONS.length - 1]!.value,
  );

  const sessionShort =
    sessionId.length > 14 ? `${sessionId.slice(0, 8)}…${sessionId.slice(-4)}` : sessionId;

  const fieldClass =
    "mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 shadow-sm outline-none transition focus:border-[var(--sbs-navy-mid)] focus:ring-2 focus:ring-[var(--sbs-navy-mid)]/20 disabled:cursor-not-allowed disabled:bg-slate-50";

  return (
    <div className={CH_SHELL}>
      {toast ? (
        <div
          role="status"
          className={
            toast.kind === "error"
              ? "rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900 shadow-sm"
              : "rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900 shadow-sm"
          }
        >
          {toast.text}
        </div>
      ) : null}

      <EnterprisePageHeader
        eyebrow="Enterprise · EU AI Act"
        title="Self-Assessment Run"
        description={
          <div className="space-y-2">
            <p className="font-mono text-sm text-slate-600">
              Session <span className="text-slate-900">{sessionShort}</span>
            </p>
            <p className="text-base text-slate-600">
              <span className={`${CH_BADGE} ${statusBadgeTone(String(session.status))}`}>
                {String(session.status)}
              </span>
              <span className="mx-2 text-slate-300" aria-hidden>
                ·
              </span>
              KI-System:{" "}
              <span className="font-medium text-slate-800">
                {session.ai_system_name ?? session.ai_system_id ?? "—"}
              </span>
            </p>
          </div>
        }
        breadcrumbs={[
          { label: "Tenant", href: "/tenant/compliance-overview" },
          { label: "Self-Assessments", href: TENANT_AI_ACT_SELF_ASSESSMENTS_PATH },
          { label: sessionShort },
        ]}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Link href={TENANT_AI_ACT_SELF_ASSESSMENTS_PATH} className={CH_BTN_SECONDARY}>
              Zur Übersicht
            </Link>
          </div>
        }
      />

      <article className={CH_CARD}>
        <p className={CH_SECTION_LABEL}>Metadaten & Aktionen</p>
        <dl className="mt-4 grid gap-4 text-sm text-slate-700 sm:grid-cols-2">
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Owner</dt>
            <dd className="mt-1 font-semibold text-slate-900">{ownerLabel}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Schema-Version
            </dt>
            <dd className="mt-1 font-semibold text-slate-900">{session.schema_version ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Gestartet</dt>
            <dd className="mt-1 font-semibold text-slate-900">{formatTs(session.started_at)}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Abgeschlossen
            </dt>
            <dd className="mt-1 font-semibold text-slate-900">{formatTs(session.completed_at)}</dd>
          </div>
        </dl>

        {inlineError ? (
          <p className="mt-4 text-sm text-rose-800" role="alert">
            {inlineError}
          </p>
        ) : null}

        <div className="mt-6 flex flex-wrap gap-2 border-t border-slate-200/80 pt-6">
          <button
            type="button"
            disabled={readOnly || actionBusy !== null || session.status === "in_review"}
            onClick={() => void onSetInReview()}
            className={`${CH_BTN_SECONDARY} disabled:pointer-events-none disabled:opacity-40`}
          >
            {actionBusy === "review" ? "Bitte warten…" : "Status auf „In Review“ setzen"}
          </button>
          <button
            type="button"
            disabled={readOnly || actionBusy !== null}
            onClick={() => void onComplete()}
            className={`${CH_BTN_PRIMARY} disabled:pointer-events-none disabled:opacity-40`}
          >
            {actionBusy === "complete" ? "Bitte warten…" : "Run abschließen"}
          </button>
          <button
            type="button"
            disabled={actionBusy !== null}
            onClick={() => void onExport()}
            className={`${CH_BTN_SECONDARY} disabled:pointer-events-none disabled:opacity-40`}
          >
            {actionBusy === "export" ? "Export…" : "Export (PDF)"}
          </button>
        </div>
      </article>

      <div
        className="flex flex-wrap gap-2 border-b border-slate-200/80 pb-1"
        role="tablist"
        aria-label="Self-Assessment Bereiche"
      >
        {(
          [
            ["questionnaire", "Fragebogen"],
            ["classification", "Klassifikation"],
            ["audit", "Audit-Trail"],
          ] as const
        ).map(([k, label]) => (
          <button
            key={k}
            type="button"
            role="tab"
            aria-selected={tab === k}
            onClick={() => setTab(k)}
            className={
              tab === k
                ? "rounded-xl bg-[var(--sbs-navy-mid)] px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-[var(--sbs-navy-deep)]"
                : "rounded-xl px-4 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-100 hover:text-slate-900"
            }
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "questionnaire" ? (
        <article className={CH_CARD}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className={CH_SECTION_LABEL}>Fragebogen</p>
              <h2 className="mt-1 text-lg font-semibold text-slate-900">Eingaben</h2>
            </div>
            <p className="text-xs text-slate-500" aria-live="polite">
              {readOnly ? (
                <span className="font-medium text-slate-700">Abgeschlossen — nur Lesen.</span>
              ) : saveState === "saving" ? (
                <span className="font-medium text-[var(--sbs-navy-deep)]">Speichern…</span>
              ) : saveState === "saved" && savedAt ? (
                <span className="font-medium text-emerald-800">
                  Gespeichert um {formatClock(savedAt)}
                </span>
              ) : saveState === "error" ? (
                <span className="font-medium text-rose-800">Letzter Speicherversuch fehlgeschlagen</span>
              ) : (
                <span>Änderungen werden automatisch gespeichert.</span>
              )}
            </p>
          </div>

          {initialAnswersError ? (
            <p className="mt-4 text-sm text-amber-900" role="alert">
              Antworten konnten beim ersten Laden nicht geladen werden: {initialAnswersError}
            </p>
          ) : null}

          <div className="mt-6 grid gap-6 sm:grid-cols-2">
            <label className="block text-sm">
              <span className="font-medium text-slate-800">Einsatzbereich (intended_use_domain)</span>
              <select
                className={fieldClass}
                disabled={readOnly}
                value={DOMAIN_OPTIONS.some((o) => o.value === domainValue) ? domainValue : "Other"}
                onChange={(e) => setAnswerField("intended_use_domain", e.target.value)}
              >
                {DOMAIN_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>

            {(
              [
                ["interacts_with_humans", "Interagiert mit Menschen"],
                ["uses_personal_data", "Verarbeitet personenbezogene Daten"],
                ["uses_biometric_identification", "Biometrische Identifikation"],
                ["is_gpai_model", "General Purpose AI (GPAI) / Foundation Model"],
                ["performs_automated_decision_making", "Automatisierte Entscheidungsfindung"],
                ["monitors_public_spaces", "Überwachung öffentlicher Räume"],
                ["safety_component_of_product", "Sicherheitskomponente eines Produkts"],
                ["uses_emotion_recognition", "Emotionserkennung"],
              ] as const
            ).map(([key, label]) => (
              <label
                key={key}
                className="flex items-center justify-between gap-3 rounded-xl border border-slate-200/80 bg-slate-50/40 px-3 py-3 text-sm"
              >
                <span className="text-slate-800">{label}</span>
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-slate-300 text-[var(--sbs-navy-mid)] focus:ring-[var(--sbs-navy-mid)] disabled:cursor-not-allowed"
                  disabled={readOnly}
                  checked={asBool(answers[key])}
                  onChange={(e) => setAnswerField(key, e.target.checked)}
                />
              </label>
            ))}
          </div>

          <label className="mt-6 block text-sm">
            <span className="font-medium text-slate-800">
              Dokumentationsreife (documentation_maturity)
            </span>
            <select
              className={`${fieldClass} max-w-md`}
              disabled={readOnly}
              value={asString(answers.documentation_maturity, "basic")}
              onChange={(e) => setAnswerField("documentation_maturity", e.target.value)}
            >
              <option value="basic">Basis</option>
              <option value="structured">Strukturiert</option>
              <option value="full">Vollständig / auditierbar</option>
            </select>
          </label>
        </article>
      ) : null}

      {tab === "classification" ? (
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Risiko & Begründung</p>
          <h2 className="mt-1 text-lg font-semibold text-slate-900">Klassifikation</h2>
          {session.status !== "completed" ? (
            <p className="mt-4 text-sm leading-relaxed text-slate-600">
              Die Klassifikation steht erst nach Abschluss des Runs zur Verfügung. Bitte zuerst
              „Run abschließen“ ausführen.
            </p>
          ) : initialClassificationError ? (
            <p className="mt-4 text-sm text-rose-800" role="alert">
              {initialClassificationError}
            </p>
          ) : classification ? (
            <div className={`mt-4 space-y-4 text-sm ${CH_CARD_MUTED}`}>
              <div>
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  risk_level
                </div>
                <div className="mt-1 text-base font-semibold text-slate-900">
                  {classification.risk_level ?? "—"}
                </div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  requires_manual_review
                </div>
                <div className="mt-1 font-medium text-slate-800">
                  {classification.requires_manual_review == null
                    ? "—"
                    : classification.requires_manual_review
                      ? "Ja"
                      : "Nein"}
                </div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  rationale
                </div>
                <p className="mt-1 whitespace-pre-wrap text-slate-800">
                  {classification.rationale ?? "—"}
                </p>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  eu_ai_act_refs
                </div>
                {classification.eu_ai_act_refs?.length ? (
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-slate-800">
                    {classification.eu_ai_act_refs.map((ref) => (
                      <li key={ref}>{ref}</li>
                    ))}
                  </ul>
                ) : (
                  <div className="mt-1">—</div>
                )}
              </div>
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-600">Keine Klassifikationsdaten geliefert.</p>
          )}
        </article>
      ) : null}

      {tab === "audit" ? (
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Nachvollziehbarkeit</p>
          <h2 className="mt-1 text-lg font-semibold text-slate-900">Audit-Trail</h2>
          {initialAuditError ? (
            <p className="mt-4 text-sm text-amber-900" role="alert">
              Audit-Events konnten beim ersten Laden nicht geladen werden: {initialAuditError}
            </p>
          ) : null}
          <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200/80">
            <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
              <thead className="bg-slate-50/90 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3">Ereignis</th>
                  <th className="px-4 py-3">Nutzer</th>
                  <th className="px-4 py-3">Zeitpunkt</th>
                  <th className="px-4 py-3">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {audit.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-slate-500">
                      Keine Events.
                    </td>
                  </tr>
                ) : (
                  audit.map((e, i) => (
                    <tr key={`${auditWhen(e)}-${i}`} className="hover:bg-slate-50/80">
                      <td className="px-4 py-3 font-medium text-slate-900">{auditEventType(e)}</td>
                      <td className="px-4 py-3 text-slate-700">{auditActor(e)}</td>
                      <td className="px-4 py-3 text-slate-600">{formatTs(auditWhen(e))}</td>
                      <td
                        className="max-w-md truncate px-4 py-3 text-slate-600"
                        title={auditDetails(e)}
                      >
                        {auditDetails(e)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          <button
            type="button"
            className={`${CH_BTN_GHOST} mt-4`}
            onClick={() => void refreshAudit()}
          >
            Audit-Liste aktualisieren
          </button>
        </article>
      ) : null}
    </div>
  );
}
