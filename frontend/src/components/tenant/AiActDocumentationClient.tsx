"use client";

import React, { useCallback, useEffect, useState } from "react";

import {
  downloadAiActDocumentationMarkdown,
  fetchAiActDocList,
  persistAiActDocSection,
  postAiActDocDraft,
  type AIActDocListItemPayload,
  type AIActDocSectionKey,
} from "@/lib/api";
import { CH_BTN_PRIMARY, CH_BTN_SECONDARY } from "@/lib/boardLayout";
import {
  featureAiActDocs,
  featureLlmEnabled,
  featureLlmLegalReasoning,
  featureLlmReportAssistant,
} from "@/lib/config";

type Props = {
  aiSystemId: string;
};

const SECTION_ORDER: AIActDocSectionKey[] = [
  "RISK_MANAGEMENT",
  "DATA_GOVERNANCE",
  "MONITORING_LOGGING",
  "HUMAN_OVERSIGHT",
  "TECHNICAL_ROBUSTNESS",
];

function statusLabel(status: string, hasDraftInEditor: boolean): string {
  if (hasDraftInEditor) return "KI-Entwurf (nicht gespeichert)";
  if (status === "saved") return "Gespeichert";
  return "Leer";
}

export function AiActDocumentationClient({ aiSystemId }: Props) {
  const enabled = featureAiActDocs();
  const llmDraftEnabled =
    featureLlmEnabled() && featureLlmLegalReasoning() && featureLlmReportAssistant();

  const [items, setItems] = useState<AIActDocListItemPayload[] | null>(null);
  const [loadErr, setLoadErr] = useState<string | null>(null);
  const [open, setOpen] = useState<AIActDocSectionKey | null>("RISK_MANAGEMENT");
  const [titleDraft, setTitleDraft] = useState("");
  const [mdDraft, setMdDraft] = useState("");
  const [preview, setPreview] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoadErr(null);
    try {
      const res = await fetchAiActDocList(aiSystemId);
      setItems(res.items);
    } catch (e) {
      setLoadErr(e instanceof Error ? e.message : "Laden fehlgeschlagen");
    }
  }, [aiSystemId]);

  useEffect(() => {
    if (!enabled) return;
    void refresh();
  }, [enabled, refresh]);

  useEffect(() => {
    if (!items || !open) return;
    const row = items.find((i) => i.section_key === open);
    if (!row) return;
    const t = row.doc?.title ?? row.default_title;
    const c = row.doc?.content_markdown ?? "";
    setTitleDraft(t);
    setMdDraft(c);
    setDirty(false);
  }, [items, open]);

  if (!enabled) return null;

  const onPickSection = (key: AIActDocSectionKey) => {
    setOpen(key);
    setMsg(null);
  };

  const onGenerateDraft = async () => {
    if (!open || !llmDraftEnabled) return;
    setBusy("draft");
    setMsg(null);
    try {
      const d = await postAiActDocDraft(aiSystemId, open);
      setTitleDraft(d.title);
      setMdDraft(d.content_markdown);
      setDirty(true);
      setPreview(false);
      setMsg("KI-Entwurf erzeugt – bitte prüfen und speichern.");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Entwurf fehlgeschlagen");
    } finally {
      setBusy(null);
    }
  };

  const onSave = async () => {
    if (!open) return;
    setBusy("save");
    setMsg(null);
    try {
      await persistAiActDocSection(aiSystemId, open, {
        title: titleDraft.trim() || "Abschnitt",
        content_markdown: mdDraft,
      });
      setDirty(false);
      await refresh();
      setMsg("Gespeichert.");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Speichern fehlgeschlagen");
    } finally {
      setBusy(null);
    }
  };

  const onExport = async () => {
    setBusy("export");
    setMsg(null);
    try {
      await downloadAiActDocumentationMarkdown(aiSystemId);
      setMsg("Download gestartet.");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Export fehlgeschlagen");
    } finally {
      setBusy(null);
    }
  };

  if (loadErr) {
    return (
      <section
        className="rounded-2xl border border-rose-200 bg-rose-50/80 px-4 py-3 text-sm text-rose-900"
        aria-label="EU AI Act Dokumentation"
      >
        <p className="font-semibold">EU AI Act Dokumentation</p>
        <p className="mt-1">{loadErr}</p>
      </section>
    );
  }

  if (!items) {
    return (
      <section className="text-sm text-slate-500" aria-label="EU AI Act Dokumentation">
        Dokumentationssektionen werden geladen…
      </section>
    );
  }

  const current = open ? items.find((i) => i.section_key === open) : null;
  const hasDraftInEditor = dirty;

  return (
    <section
      id="sec-ai-act-docs"
      className="scroll-mt-32 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
      aria-label="EU AI Act Dokumentation"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-slate-900">EU AI Act Dokumentation</h2>
          <p className="mt-1 text-xs text-slate-500">
            Annex-IV-/Art.-11-orientierte Bausteine für High-Risk-Systeme. KI-Entwürfe sind
            Prüftexte ohne Rechtsberatung; Inhalt vor Freigabe validieren.
          </p>
        </div>
        <button type="button" className={CH_BTN_SECONDARY} onClick={() => void onExport()} disabled={!!busy}>
          AI Act Dokumentation herunterladen (MD)
        </button>
      </div>

      <p className="mt-3 text-xs text-amber-800/90">
        Hinweis: Export und Sektionen setzen das Backend-Feature{" "}
        <code className="rounded bg-amber-100/80 px-1">COMPLIANCEHUB_FEATURE_AI_ACT_DOCS</code> voraus.
      </p>

      <div className="mt-4 flex flex-col gap-2 md:flex-row">
        <nav className="md:w-56 md:shrink-0" aria-label="Dokumentationssektionen">
          <ul className="space-y-1">
            {SECTION_ORDER.map((key) => {
              const row = items.find((i) => i.section_key === key);
              if (!row) return null;
              const active = open === key;
              return (
                <li key={key}>
                  <button
                    type="button"
                    onClick={() => onPickSection(key)}
                    className={`w-full rounded-lg px-3 py-2 text-left text-sm font-medium transition ${
                      active
                        ? "bg-cyan-50 text-cyan-950 ring-1 ring-cyan-200"
                        : "text-slate-700 hover:bg-slate-50"
                    }`}
                  >
                    <span className="block truncate">{row.default_title}</span>
                    <span className="mt-0.5 block text-[0.65rem] font-normal uppercase tracking-wide text-slate-500">
                      {statusLabel(row.status, active && hasDraftInEditor)}
                      {row.doc ? ` · v${row.doc.version}` : ""}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="min-w-0 flex-1 space-y-3">
          {current && open ? (
            <>
              <div className="flex flex-wrap gap-2">
                {llmDraftEnabled ? (
                  <button
                    type="button"
                    className={CH_BTN_SECONDARY}
                    disabled={!!busy}
                    onClick={() => void onGenerateDraft()}
                  >
                    {busy === "draft" ? "KI arbeitet…" : "KI-Entwurf erzeugen"}
                  </button>
                ) : (
                  <p className="text-xs text-slate-500">
                    KI-Entwurf: LLM-Features (Legal Reasoning + strukturierte Ausgabe) sind im UI
                    deaktiviert.
                  </p>
                )}
                <button
                  type="button"
                  className={CH_BTN_PRIMARY}
                  disabled={!!busy}
                  onClick={() => void onSave()}
                >
                  {busy === "save" ? "Speichern…" : "Speichern"}
                </button>
                <button
                  type="button"
                  className={CH_BTN_SECONDARY}
                  onClick={() => setPreview((p) => !p)}
                >
                  {preview ? "Rohtext" : "Vorschau"}
                </button>
              </div>
              <label className="block text-xs font-medium text-slate-600">
                Titel
                <input
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                  value={titleDraft}
                  onChange={(e) => {
                    setTitleDraft(e.target.value);
                    setDirty(true);
                  }}
                />
              </label>
              {preview ? (
                <div
                  className="prose prose-sm max-w-none rounded-xl border border-slate-100 bg-slate-50/80 p-4 text-slate-800"
                  data-testid="ai-act-md-preview"
                >
                  <h3 className="text-base font-semibold">{titleDraft}</h3>
                  <div className="whitespace-pre-wrap font-sans text-sm">{mdDraft}</div>
                </div>
              ) : (
                <label className="block text-xs font-medium text-slate-600">
                  Markdown
                  <textarea
                    className="mt-1 min-h-[220px] w-full rounded-lg border border-slate-200 px-3 py-2 font-mono text-sm"
                    value={mdDraft}
                    onChange={(e) => {
                      setMdDraft(e.target.value);
                      setDirty(true);
                    }}
                  />
                </label>
              )}
            </>
          ) : null}
          {msg ? (
            <p className="text-sm text-slate-700" role="status">
              {msg}
            </p>
          ) : null}
        </div>
      </div>
    </section>
  );
}
