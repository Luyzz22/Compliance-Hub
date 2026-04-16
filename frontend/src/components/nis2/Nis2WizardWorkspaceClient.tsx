"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { AuditTrailPanel } from "@/components/governance/AuditTrailPanel";
import { GovernanceWorkspaceLayout } from "@/components/governance/GovernanceWorkspaceLayout";
import { StatusBadge } from "@/components/governance/StatusBadge";
import { CH_BTN_SECONDARY, CH_CARD, CH_SECTION_LABEL } from "@/lib/boardLayout";
import { formatGovernanceDateTime } from "@/lib/formatGovernanceDate";
import { computeNis2Readiness } from "@/lib/nis2InScopeScore";
import {
  completeNis2WizardSession,
  exportNis2WizardSession,
  mapNis2AuditStubsToRows,
  saveNis2WizardAnswer,
  type Nis2WizardAuditEventStub,
} from "@/lib/nis2WizardApi";
import { NIS2_WIZARD_KEYS, type Nis2WizardSession, type Nis2WizardSessionStatus } from "@/lib/nis2WizardModels";
import { TENANT_NIS2_WIZARD_BASE } from "@/lib/nis2WizardRoutes";

const STEPS = [
  { id: 0, title: "Basisdaten", short: "Größe" },
  { id: 1, title: "Sektor & Dienste", short: "Sektor" },
  { id: 2, title: "Lieferkette", short: "Supply" },
  { id: 3, title: "Governance-Status", short: "ISM" },
] as const;

export interface Nis2WizardWorkspaceClientProps {
  tenantId: string;
  sessionId: string;
  initialSession: Nis2WizardSession;
  initialAnswers: Record<string, unknown>;
  initialAudit: Nis2WizardAuditEventStub[];
  initialAnswersError?: string | null;
  initialAuditError?: string | null;
}

export function Nis2WizardWorkspaceClient({
  tenantId,
  sessionId,
  initialSession,
  initialAnswers,
  initialAudit,
  initialAnswersError,
  initialAuditError,
}: Nis2WizardWorkspaceClientProps) {
  const [tab, setTab] = useState<"wizard" | "result" | "audit">("wizard");
  const [wizardStep, setWizardStep] = useState(0);
  const [session, setSession] = useState(initialSession);
  const [answers, setAnswers] = useState<Record<string, unknown>>(initialAnswers);
  const [auditStubs, setAuditStubs] = useState<Nis2WizardAuditEventStub[]>(initialAudit);

  const [toast, setToast] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [inlineError, setInlineError] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState<"review" | "complete" | "export" | null>(null);

  const timers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  const latestByKey = useRef<Record<string, unknown>>({});
  const inflightSaves = useRef<Promise<void>[]>([]);

  const readOnly = session.status === "completed";

  const readiness = useMemo(() => computeNis2Readiness(answers), [answers]);

  const auditRows = useMemo(() => mapNis2AuditStubsToRows(auditStubs), [auditStubs]);

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
    setAuditStubs(initialAudit);
  }, [initialAudit]);

  const showToast = useCallback((kind: "success" | "error", text: string) => {
    setToast({ kind, text });
    window.setTimeout(() => setToast(null), 6000);
  }, []);

  const appendAudit = useCallback((eventType: string, details: string) => {
    setAuditStubs((prev) => [
      ...prev,
      {
        event_type: eventType,
        user: "mandant-user",
        timestamp: new Date().toISOString(),
        details,
      },
    ]);
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
          const res = await saveNis2WizardAnswer(tenantId, sessionId, questionKey, value);
          if (!res.ok) {
            setSaveState("error");
            setInlineError(`${res.status}: ${res.message}`);
            showToast("error", `Speichern fehlgeschlagen (${res.status})`);
            return;
          }
          setSaveState("saved");
          setSavedAt(new Date().toISOString());
          appendAudit("answer_saved", `${questionKey} aktualisiert (Stub).`);
        })();
        trackInflightSave(p);
      }, 450);
    },
    [appendAudit, readOnly, sessionId, showToast, tenantId],
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
      const res = await saveNis2WizardAnswer(tenantId, sessionId, key, value);
      if (!res.ok) {
        return { ok: false, status: res.status, message: res.message };
      }
      setSaveState("saved");
      setSavedAt(new Date().toISOString());
      appendAudit("answer_saved", `${key} geflusht (Stub).`);
    }
    await drainInflightSaves();
    return { ok: true };
  }, [appendAudit, drainInflightSaves, sessionId, tenantId]);

  useEffect(() => {
    return () => {
      for (const t of Object.values(timers.current)) {
        clearTimeout(t);
      }
    };
  }, []);

  const setAnswerField = useCallback(
    (key: string, value: unknown) => {
      setAnswers((prev) => ({ ...prev, [key]: value }));
      scheduleSave(key, value);
    },
    [scheduleSave],
  );

  async function onMarkInProgress() {
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
    setActionBusy(null);
    setSession((s) => ({ ...s, status: "in_progress" as Nis2WizardSessionStatus }));
    appendAudit("status_marked", "Als „in Bearbeitung“ markiert (lokal, Stub).");
    showToast("success", "Status aktualisiert.");
  }

  async function onCompleteWizard() {
    setInlineError(null);
    setActionBusy("complete");
    const flush = await flushPendingAutosaves();
    if (!flush.ok) {
      setActionBusy(null);
      setInlineError(`${flush.status}: ${flush.message}`);
      showToast("error", flush.message);
      setSaveState("error");
      return;
    }
    const res = await completeNis2WizardSession(tenantId, sessionId);
    setActionBusy(null);
    if (!res.ok) {
      setInlineError(`${res.status}: ${res.message}`);
      showToast("error", res.message);
      return;
    }
    setSession(res.data);
    appendAudit("wizard_completed", "Wizard abgeschlossen (Stub-API).");
    showToast("success", "Wizard abgeschlossen.");
    setTab("result");
  }

  async function onExportStub() {
    setInlineError(null);
    setActionBusy("export");
    const res = await exportNis2WizardSession(tenantId, sessionId);
    setActionBusy(null);
    if (!res.ok) {
      setInlineError(`${res.status}: ${res.message}`);
      showToast("error", res.message);
      return;
    }
    if (res.data.download_url) {
      window.open(res.data.download_url, "_blank", "noopener,noreferrer");
    } else {
      showToast("success", "Export-Stub: noch kein Download-Link (TODO Backend).");
    }
    appendAudit("export_requested", "Export angefragt (Stub).");
  }

  const sessionShort =
    sessionId.length > 14 ? `${sessionId.slice(0, 8)}…${sessionId.slice(-4)}` : sessionId;

  const fieldClass =
    "mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 shadow-sm outline-none transition focus:border-[var(--sbs-navy-mid)] focus:ring-2 focus:ring-[var(--sbs-navy-mid)]/20 disabled:cursor-not-allowed disabled:bg-slate-50";

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
        NIS2 / KRITIS-DACH — Readiness as a Service (Indikation, keine Rechtsberatung).
      </p>
    </div>
  );

  const metadataSection = (
    <dl className="grid gap-4 text-sm text-slate-700 sm:grid-cols-2">
      <div>
        <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Schema</dt>
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
      <div>
        <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Mandant</dt>
        <dd className="mt-1 font-mono text-xs text-slate-800">{tenantId}</dd>
      </div>
    </dl>
  );

  const wizardPanel = (
    <article className={CH_CARD}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className={CH_SECTION_LABEL}>Wizard</p>
          <h2 className="mt-1 text-lg font-semibold text-slate-900">NIS2 / KRITIS — Einstufung</h2>
        </div>
        <p className="text-xs text-slate-500" aria-live="polite">
          {readOnly ? (
            <span className="font-medium text-slate-700">Abgeschlossen — nur Lesen.</span>
          ) : saveState === "saving" ? (
            <span className="font-medium text-[var(--sbs-navy-deep)]">Speichern…</span>
          ) : saveState === "saved" && savedAt ? (
            <span className="font-medium text-emerald-800">
              Gespeichert {formatGovernanceDateTime(savedAt)}
            </span>
          ) : saveState === "error" ? (
            <span className="font-medium text-rose-800">Speichern fehlgeschlagen</span>
          ) : (
            <span>Antworten werden automatisch gespeichert (Stub).</span>
          )}
        </p>
      </div>

      {initialAnswersError ? (
        <p className="mt-4 text-sm text-amber-900" role="alert">
          Antworten konnten nicht geladen werden: {initialAnswersError}
        </p>
      ) : null}

      <ol className="mt-6 flex flex-wrap gap-2" aria-label="Wizard-Schritte">
        {STEPS.map((s, idx) => (
          <li key={s.id}>
            <button
              type="button"
              disabled={readOnly}
              onClick={() => setWizardStep(idx)}
              className={
                wizardStep === idx
                  ? "rounded-full bg-[var(--sbs-navy-mid)] px-3 py-1.5 text-xs font-semibold text-white"
                  : "rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
              }
            >
              {idx + 1}. {s.short}
            </button>
          </li>
        ))}
      </ol>

      <div className="mt-6 space-y-6">
        {wizardStep === 0 ? (
          <>
            <label className="block text-sm">
              <span className="font-medium text-slate-800">Unternehmensgröße (Mitarbeitende)</span>
              <select
                className={fieldClass}
                disabled={readOnly}
                value={String(answers[NIS2_WIZARD_KEYS.employeeBucket] ?? "small")}
                onChange={(e) => setAnswerField(NIS2_WIZARD_KEYS.employeeBucket, e.target.value)}
              >
                <option value="micro">1–9 (Klein)</option>
                <option value="small">10–49</option>
                <option value="medium">50–249</option>
                <option value="large">250–499</option>
                <option value="enterprise">500+</option>
              </select>
            </label>
            <label className="block text-sm">
              <span className="font-medium text-slate-800">Umsatz-Bucket (Indikator)</span>
              <select
                className={fieldClass}
                disabled={readOnly}
                value={String(answers[NIS2_WIZARD_KEYS.revenueBucket] ?? "unknown")}
                onChange={(e) => setAnswerField(NIS2_WIZARD_KEYS.revenueBucket, e.target.value)}
              >
                <option value="unknown">Unbekannt / nicht zuordenbar</option>
                <option value="under_50m">unter 50 Mio. €</option>
                <option value="50_250m">50–250 Mio. €</option>
                <option value="over_250m">über 250 Mio. €</option>
              </select>
            </label>
          </>
        ) : null}

        {wizardStep === 1 ? (
          <>
            <label className="block text-sm">
              <span className="font-medium text-slate-800">Sektor (vereinfacht)</span>
              <select
                className={fieldClass}
                disabled={readOnly}
                value={String(answers[NIS2_WIZARD_KEYS.sector] ?? "other")}
                onChange={(e) => setAnswerField(NIS2_WIZARD_KEYS.sector, e.target.value)}
              >
                <option value="energy">Energie</option>
                <option value="health">Gesundheitswesen</option>
                <option value="transport">Transport / Verkehr</option>
                <option value="digital_provider">Digitaler Dienstleister / IT-Dienstleistung</option>
                <option value="finance">Finanz / Versicherung</option>
                <option value="other">Sonstige</option>
              </select>
            </label>
            <fieldset className="space-y-2 text-sm">
              <legend className="font-medium text-slate-800">
                Erbringst du „wesentliche digitale Dienste“ (indikativ)?
              </legend>
              {(
                [
                  ["yes", "Ja"],
                  ["no", "Nein"],
                  ["unsure", "Unsicher"],
                ] as const
              ).map(([v, label]) => (
                <label key={v} className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="eds"
                    disabled={readOnly}
                    checked={answers[NIS2_WIZARD_KEYS.essentialDigitalServices] === v}
                    onChange={() => setAnswerField(NIS2_WIZARD_KEYS.essentialDigitalServices, v)}
                  />
                  {label}
                </label>
              ))}
            </fieldset>
          </>
        ) : null}

        {wizardStep === 2 ? (
          <fieldset className="space-y-2 text-sm">
            <legend className="font-medium text-slate-800">
              Bist du Zulieferer einer bereits NIS2-pflichtigen Organisation?
            </legend>
            {(
              [
                ["yes", "Ja"],
                ["no", "Nein"],
                ["unsure", "Unklar"],
              ] as const
            ).map(([v, label]) => (
              <label key={v} className="flex items-center gap-2">
                <input
                  type="radio"
                  name="sup"
                  disabled={readOnly}
                  checked={answers[NIS2_WIZARD_KEYS.supplierToNis2Entity] === v}
                  onChange={() => setAnswerField(NIS2_WIZARD_KEYS.supplierToNis2Entity, v)}
                />
                {label}
              </label>
            ))}
          </fieldset>
        ) : null}

        {wizardStep === 3 ? (
          <label className="block text-sm">
            <span className="font-medium text-slate-800">
              Governance / Informationssicherheits-Management
            </span>
            <select
              className={fieldClass}
              disabled={readOnly}
              value={String(answers[NIS2_WIZARD_KEYS.governanceMaturity] ?? "basic")}
              onChange={(e) => setAnswerField(NIS2_WIZARD_KEYS.governanceMaturity, e.target.value)}
            >
              <option value="none">Kein formales Programm</option>
              <option value="basic">Grundlegende Maßnahmen</option>
              <option value="isms_partial">ISMS teilweise etabliert</option>
              <option value="isms_established">ISMS etabliert / zertifizierungsreif</option>
            </select>
          </label>
        ) : null}
      </div>

      <div className="mt-8 flex flex-wrap justify-between gap-2 border-t border-slate-200/80 pt-6">
        <button
          type="button"
          disabled={readOnly || wizardStep === 0}
          className={`${CH_BTN_SECONDARY} disabled:opacity-40`}
          onClick={() => setWizardStep((s) => Math.max(0, s - 1))}
        >
          Zurück
        </button>
        <button
          type="button"
          disabled={readOnly || wizardStep >= STEPS.length - 1}
          className={`${CH_BTN_SECONDARY} disabled:opacity-40`}
          onClick={() => setWizardStep((s) => Math.min(STEPS.length - 1, s + 1))}
        >
          Weiter
        </button>
      </div>
    </article>
  );

  const resultPanel = (
    <article className={CH_CARD}>
      <p className={CH_SECTION_LABEL}>Ergebnis</p>
      <h2 className="mt-1 text-lg font-semibold text-slate-900">InScope-Indikation</h2>
      <p className="mt-2 text-sm text-slate-600">
        Score und Einstufung sind clientseitige Heuristik —{" "}
        <strong className="font-medium text-slate-800">keine Rechtsberatung</strong>. TODO:
        serverseitige Regelengine (BSIG/KRITIS-Referenzen).
      </p>
      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">InScope-Score</p>
          <p className="mt-2 text-4xl font-bold tabular-nums text-[var(--sbs-navy-deep)]">
            {readiness.inScopeScore}
          </p>
          <p className="mt-1 text-sm text-slate-600">von 100 (Indikation „wahrscheinlich NIS2-relevant“)</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">NIS2-Exposure</p>
          <p className="mt-2 text-2xl font-semibold capitalize text-slate-900">{readiness.exposure}</p>
          <p className="mt-1 text-sm text-slate-600">
            Kritische Organisation (light):{" "}
            <strong>{readiness.criticalOrganizationLight ? "Ja (Indikation)" : "Nein"}</strong>
          </p>
        </div>
      </div>
      <div className="mt-6">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Empfohlene Control-Cluster (Stub)
        </p>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-800">
          {readiness.recommendedControlClusters.map((c) => (
            <li key={c}>
              <code className="rounded bg-slate-100 px-1 py-0.5 text-xs">{c}</code>
            </li>
          ))}
        </ul>
      </div>
      <div className="mt-6">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Nächste Schritte</p>
        <ul className="mt-2 list-decimal space-y-2 pl-5 text-sm text-slate-700">
          {readiness.nextSteps.map((t, i) => (
            <li key={i}>{t}</li>
          ))}
        </ul>
      </div>
    </article>
  );

  const handleAuditRefresh = useCallback(async () => {
    /* TODO: GET /api/v1/audit/nis2-wizard/sessions/{id}/events — bis dahin nur lokaler State */
    showToast("success", "Aktualisierung: aktuell nur lokaler Stub.");
  }, [showToast]);

  const tabs = [
    { id: "wizard" as const, label: "Wizard", content: wizardPanel },
    { id: "result" as const, label: "Ergebnis", content: resultPanel },
    {
      id: "audit" as const,
      label: "Audit-Trail",
      content: (
        <AuditTrailPanel
          rows={auditRows}
          initialLoadError={initialAuditError ?? undefined}
          onRefresh={handleAuditRefresh}
        />
      ),
    },
  ];

  return (
    <GovernanceWorkspaceLayout
      title="NIS2 / KRITIS Wizard"
      eyebrow="Enterprise · Block 3"
      status={String(session.status)}
      headerDescription={headerDescription}
      breadcrumbs={[
        { label: "Tenant", href: "/tenant/compliance-overview" },
        { label: "NIS2 Wizard", href: TENANT_NIS2_WIZARD_BASE },
        { label: sessionShort },
      ]}
      headerActions={
        <Link href={TENANT_NIS2_WIZARD_BASE} className={CH_BTN_SECONDARY}>
          Zur Wizard-Übersicht
        </Link>
      }
      toast={toast}
      metadataSection={metadataSection}
      actionError={inlineError}
      onStatusChange={onMarkInProgress}
      onComplete={onCompleteWizard}
      onExport={onExportStub}
      statusChangeDisabled={readOnly}
      completeDisabled={readOnly}
      exportDisabled={readOnly}
      busyAction={actionBusy}
      labels={{
        statusChange: "Als in Bearbeitung markieren",
        complete: "Wizard abschließen",
        export: "Bericht (Stub)",
      }}
      tabs={tabs}
      activeTabId={tab}
      onTabChange={(id) => setTab(id as "wizard" | "result" | "audit")}
      tablistAriaLabel="NIS2 Wizard Bereiche"
    />
  );
}
