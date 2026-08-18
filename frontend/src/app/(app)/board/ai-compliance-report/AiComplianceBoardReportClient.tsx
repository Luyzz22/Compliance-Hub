"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";

import {
  createAiComplianceBoardReport,
  fetchAiComplianceBoardReportDetail,
  fetchAiComplianceBoardReports,
  type AiComplianceBoardReportAudience,
  type AiComplianceBoardReportDetailDto,
  type AiComplianceBoardReportListItemDto,
} from "@/lib/api";
import {
  CH_BTN_PRIMARY,
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_SECTION_LABEL,
  BOARD_PAGE_ROOT_CLASS,
} from "@/lib/boardLayout";
import { BoardReadinessCard } from "@/components/board/BoardReadinessCard";
import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import { GovernanceViewFeatureTelemetry } from "@/components/workspace/GovernanceViewFeatureTelemetry";
import { useWorkspaceMode } from "@/hooks/useWorkspaceMode";
import { DEMO_BANNER_BOARD_REPORT } from "@/lib/governanceMaturityDeCopy";

const ALL_FRAMEWORKS: { key: string; label: string }[] = [
  { key: "eu_ai_act", label: "EU AI Act" },
  { key: "nis2", label: "NIS2" },
  { key: "iso_42001", label: "ISO 42001" },
  { key: "iso_27001", label: "ISO 27001" },
  { key: "iso_27701", label: "ISO 27701" },
  { key: "dsgvo", label: "DSGVO" },
];

const mdComponents = {
  h2: (props: React.ComponentPropsWithoutRef<"h2">) => (
    <h2 className="mt-8 border-b border-slate-200 pb-1 text-base font-bold text-slate-900" {...props} />
  ),
  h3: (props: React.ComponentPropsWithoutRef<"h3">) => (
    <h3 className="mt-4 text-sm font-bold text-slate-800" {...props} />
  ),
  p: (props: React.ComponentPropsWithoutRef<"p">) => (
    <p className="mt-2 text-sm leading-relaxed text-slate-700" {...props} />
  ),
  ul: (props: React.ComponentPropsWithoutRef<"ul">) => (
    <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-slate-700" {...props} />
  ),
  ol: (props: React.ComponentPropsWithoutRef<"ol">) => (
    <ol className="mt-2 list-inside list-decimal space-y-1 text-sm text-slate-700" {...props} />
  ),
  li: (props: React.ComponentPropsWithoutRef<"li">) => <li className="pl-0.5" {...props} />,
  strong: (props: React.ComponentPropsWithoutRef<"strong">) => (
    <strong className="font-semibold text-slate-900" {...props} />
  ),
};

export function AiComplianceBoardReportClient({ tenantId }: { tenantId: string }) {
  const { mutationsBlocked, isDemoTenant } = useWorkspaceMode(tenantId);
  const [history, setHistory] = useState<AiComplianceBoardReportListItemDto[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AiComplianceBoardReportDetailDto | null>(null);
  const [loadErr, setLoadErr] = useState<string | null>(null);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [audience, setAudience] = useState<AiComplianceBoardReportAudience>("board");
  const [fwSelected, setFwSelected] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(ALL_FRAMEWORKS.map((f) => [f.key, true])),
  );
  const [aiActOnly, setAiActOnly] = useState(false);
  const [genBusy, setGenBusy] = useState(false);
  const [genErr, setGenErr] = useState<string | null>(null);

  const allFwKeys = useMemo(() => ALL_FRAMEWORKS.map((f) => f.key), []);

  const refreshHistory = useCallback(async () => {
    setLoadErr(null);
    try {
      const list = await fetchAiComplianceBoardReports(tenantId);
      setHistory(list);
      setSelectedId((prev) => prev ?? (list[0]?.id ?? null));
    } catch (e) {
      setLoadErr(e instanceof Error ? e.message : "Liste konnte nicht geladen werden");
    }
  }, [tenantId]);

  useEffect(() => {
    void refreshHistory();
  }, [refreshHistory]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const d = await fetchAiComplianceBoardReportDetail(tenantId, selectedId);
        if (!cancelled) {
          setDetail(d);
        }
      } catch {
        if (!cancelled) {
          setDetail(null);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [tenantId, selectedId]);

  const focusFrameworksForApi = (): string[] | null => {
    if (aiActOnly) {
      return null;
    }
    const on = allFwKeys.filter((k) => fwSelected[k]);
    if (on.length === allFwKeys.length) {
      return null;
    }
    return on;
  };

  const runGenerate = async () => {
    if (mutationsBlocked) {
      setGenErr("Im Demo-Mandanten (read-only) kann kein neuer Report erzeugt werden.");
      return;
    }
    setGenBusy(true);
    setGenErr(null);
    try {
      const res = await createAiComplianceBoardReport(tenantId, {
        audience_type: audience,
        focus_frameworks: focusFrameworksForApi(),
        include_ai_act_only: aiActOnly,
        language: "de",
      });
      setWizardOpen(false);
      await refreshHistory();
      setSelectedId(res.report_id);
      const d = await fetchAiComplianceBoardReportDetail(tenantId, res.report_id);
      setDetail(d);
    } catch (e) {
      setGenErr(e instanceof Error ? e.message : "Generierung fehlgeschlagen");
    } finally {
      setGenBusy(false);
    }
  };

  const copyMarkdown = async () => {
    if (!detail?.rendered_markdown) return;
    await navigator.clipboard.writeText(detail.rendered_markdown);
  };

  const exportMd = () => {
    if (!detail?.rendered_markdown) return;
    const blob = new Blob([detail.rendered_markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ai-compliance-board-report-${detail.id.slice(0, 8)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const last = history[0];

  return (
    <div className={BOARD_PAGE_ROOT_CLASS}>
      <GovernanceViewFeatureTelemetry
        tenantId={tenantId}
        featureName="board_reports_overview"
        routeName="/board/ai-compliance-report"
      />
      <EnterprisePageHeader
        eyebrow="Board"
        title="AI Compliance Board-Report"
        description="KI-generiertes Snippet aus Framework-Coverage, regulatorischen Gaps und optionalen Gap-Assist-Hinweisen – für Board-Packs und Mandantenreports (keine Rechtsberatung)."
      />

      <p className="mb-6 text-sm text-slate-500">
        Mandant: <span className="font-mono font-semibold text-slate-800">{tenantId}</span>
      </p>

      <div className="mb-6">
        <BoardReadinessCard tenantId={tenantId} isDemoTenant={isDemoTenant} />
      </div>

      {loadErr ? (
        <div className="mb-6 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900">
          {loadErr}
        </div>
      ) : null}

      {mutationsBlocked ? (
        <div
          className="mb-6 rounded-lg border border-amber-200 bg-amber-50/90 px-3 py-2 text-sm text-amber-950"
          role="status"
        >
          {DEMO_BANNER_BOARD_REPORT}
        </div>
      ) : null}

      <div className="mb-6 grid gap-4 lg:grid-cols-2">
        <article className={CH_CARD} data-testid="board-report-latest-card">
          <p className={CH_SECTION_LABEL}>Letzter Report</p>
          {last ? (
            <>
              <p className="mt-2 text-sm font-semibold text-slate-900">{last.title}</p>
              <p className="mt-1 text-xs text-slate-600">
                {new Date(last.created_at).toLocaleString("de-DE")} · Zielgruppe:{" "}
                {last.audience_type}
              </p>
              <button
                type="button"
                className={`${CH_BTN_SECONDARY} mt-3 text-xs`}
                onClick={() => setSelectedId(last.id)}
              >
                {mutationsBlocked ? "Demo-Board-Report anzeigen" : "Anzeigen"}
              </button>
            </>
          ) : (
            <p className="mt-2 text-sm text-slate-600">Noch kein Report vorhanden.</p>
          )}
        </article>
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Neu</p>
          <p className="mt-2 text-sm text-slate-600">
            Die KI analysiert Ihre aktuelle Abdeckung und erzeugt ein board-taugliches Markdown-
            Dokument.
          </p>
          <button
            type="button"
            className={`${CH_BTN_PRIMARY} mt-4 text-sm disabled:cursor-not-allowed disabled:opacity-50`}
            onClick={() => setWizardOpen(true)}
            data-testid="board-report-open-wizard"
            disabled={mutationsBlocked}
            title={
              mutationsBlocked
                ? "Demo-Mandant: keine neue Report-Generierung"
                : "Assistent zur Report-Erstellung öffnen"
            }
          >
            {mutationsBlocked ? "Demo-Report ansehen (unten)" : "Neuen Report erzeugen (KI)"}
          </button>
        </article>
      </div>

      <section className={CH_CARD} aria-label="Historie" data-testid="board-report-history">
        <p className={CH_SECTION_LABEL}>Historie</p>
        {history.length === 0 ? (
          <p className="mt-2 text-sm text-slate-600">Keine Einträge.</p>
        ) : (
          <ul className="mt-3 divide-y divide-slate-100">
            {history.map((h) => (
              <li key={h.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <div>
                  <p className="text-sm font-medium text-slate-900">{h.title}</p>
                  <p className="text-xs text-slate-500">
                    {new Date(h.created_at).toLocaleString("de-DE")} · {h.audience_type}
                  </p>
                </div>
                <button
                  type="button"
                  className={`${CH_BTN_SECONDARY} text-xs`}
                  onClick={() => setSelectedId(h.id)}
                >
                  Öffnen
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {detail ? (
        <section className={`${CH_CARD} mt-8`} data-testid="board-report-viewer">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className={CH_SECTION_LABEL}>Vorschau</p>
            <div className="flex flex-wrap gap-2">
              <button type="button" className={`${CH_BTN_SECONDARY} text-xs`} onClick={() => void copyMarkdown()}>
                In Zwischenablage kopieren
              </button>
              <button type="button" className={`${CH_BTN_SECONDARY} text-xs`} onClick={exportMd}>
                Als Markdown exportieren (.md)
              </button>
              <button
                type="button"
                className={`${CH_BTN_SECONDARY} cursor-not-allowed text-xs opacity-50`}
                disabled
                title="PDF/HTML-Export folgt (vorhandene Export-Pipeline anbinden)"
              >
                HTML/PDF (geplant)
              </button>
            </div>
          </div>
          <div className="mt-4 max-w-4xl rounded-lg border border-slate-100 bg-slate-50/50 p-4">
            <ReactMarkdown components={mdComponents}>{detail.rendered_markdown}</ReactMarkdown>
          </div>
        </section>
      ) : null}

      {wizardOpen ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="board-report-wizard-title"
        >
          <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl bg-white p-5 shadow-xl">
            <h2 id="board-report-wizard-title" className="text-lg font-bold text-slate-900">
              Report generieren
            </h2>
            <label className="mt-4 block text-xs font-semibold text-slate-600">
              Zielgruppe
              <select
                className="mt-1 w-full rounded-lg border border-slate-200 px-2 py-2 text-sm"
                value={audience}
                onChange={(e) => setAudience(e.target.value as AiComplianceBoardReportAudience)}
                data-testid="board-report-audience"
              >
                <option value="board">Vorstand / Aufsicht</option>
                <option value="management">Management</option>
                <option value="advisor_client">Mandant (Berater-Sicht)</option>
              </select>
            </label>
            <label className="mt-3 flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={aiActOnly}
                onChange={(e) => setAiActOnly(e.target.checked)}
                data-testid="board-report-ai-act-only"
              />
              Fokus nur EU AI Act (überschreibt Framework-Auswahl)
            </label>
            <p className="mt-4 text-xs font-semibold uppercase text-slate-500">Frameworks im Fokus</p>
            <div className="mt-2 space-y-2">
              {ALL_FRAMEWORKS.map((f) => (
                <label key={f.key} className="flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    disabled={aiActOnly}
                    checked={fwSelected[f.key] ?? false}
                    onChange={(e) =>
                      setFwSelected((prev) => ({ ...prev, [f.key]: e.target.checked }))
                    }
                  />
                  {f.label}
                </label>
              ))}
            </div>
            {genErr ? <p className="mt-3 text-sm text-rose-700">{genErr}</p> : null}
            {genBusy ? (
              <p className="mt-3 text-sm text-slate-600" role="status">
                Die KI analysiert Ihre aktuelle Abdeckung und generiert ein Board-taugliches Summary…
              </p>
            ) : null}
            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                className={`${CH_BTN_SECONDARY} text-xs`}
                onClick={() => setWizardOpen(false)}
                disabled={genBusy}
              >
                Abbrechen
              </button>
              <button
                type="button"
                className={`${CH_BTN_PRIMARY} text-xs`}
                onClick={() => void runGenerate()}
                disabled={genBusy}
                data-testid="board-report-generate"
              >
                Report generieren
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
