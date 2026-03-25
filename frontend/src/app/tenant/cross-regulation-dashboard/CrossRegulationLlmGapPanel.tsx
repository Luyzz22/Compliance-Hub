"use client";

import Link from "next/link";
import React, { useMemo, useState } from "react";

import {
  type CrossRegLlmGapSuggestionDto,
  type RegulatoryRequirementRowDto,
  postCrossRegulationLlmGapAssistant,
} from "@/lib/api";
import { CH_BTN_PRIMARY, CH_BTN_SECONDARY, CH_CARD, CH_SECTION_LABEL } from "@/lib/boardLayout";

type FocusPreset = "all" | "ai_act_iso42001" | "nis2_iso27001";

const FOCUS_OPTIONS: { value: FocusPreset; label: string; keys: string[] | null }[] = [
  { value: "all", label: "Alle Frameworks", keys: null },
  { value: "ai_act_iso42001", label: "AI Act & ISO 42001", keys: ["eu_ai_act", "iso_42001"] },
  { value: "nis2_iso27001", label: "NIS2 & ISO 27001", keys: ["nis2", "iso_27001"] },
];

function badgeFramework(k: string): string {
  const m: Record<string, string> = {
    eu_ai_act: "EU AI Act",
    iso_42001: "ISO 42001",
    iso_27001: "ISO 27001",
    iso_27701: "ISO 27701",
    nis2: "NIS2",
    dsgvo: "DSGVO",
  };
  return m[k] ?? k;
}

function requirementLines(
  suggestion: CrossRegLlmGapSuggestionDto,
  byId: Map<number, RegulatoryRequirementRowDto>,
): { code: string; title: string }[] {
  const out: { code: string; title: string }[] = [];
  for (const id of suggestion.requirement_ids) {
    const row = byId.get(id);
    if (row) {
      out.push({ code: row.code, title: row.title });
    } else {
      out.push({ code: `#${id}`, title: "—" });
    }
  }
  return out;
}

export interface CrossRegulationLlmGapPanelProps {
  tenantId: string;
  requirements: RegulatoryRequirementRowDto[];
}

export function CrossRegulationLlmGapPanel({ tenantId, requirements }: CrossRegulationLlmGapPanelProps) {
  const [focus, setFocus] = useState<FocusPreset>("all");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<CrossRegLlmGapSuggestionDto[]>([]);
  const [openIdx, setOpenIdx] = useState<number | null>(null);
  const [controlDraft, setControlDraft] = useState<{ name: string; description: string } | null>(
    null,
  );

  const reqById = useMemo(() => {
    const m = new Map<number, RegulatoryRequirementRowDto>();
    for (const r of requirements) {
      m.set(r.id, r);
    }
    return m;
  }, [requirements]);

  const focusKeys = useMemo(
    () => FOCUS_OPTIONS.find((o) => o.value === focus)?.keys ?? null,
    [focus],
  );

  const runAnalysis = async () => {
    setBusy(true);
    setErr(null);
    try {
      const res = await postCrossRegulationLlmGapAssistant(tenantId, {
        focus_frameworks: focusKeys ?? undefined,
        max_suggestions: 8,
      });
      setSuggestions(res.suggestions);
      setOpenIdx(null);
    } catch (e) {
      setSuggestions([]);
      setErr(
        e instanceof Error
          ? e.message
          : "Die KI-Auswertung ist fehlgeschlagen. Prüfen Sie LLM-Konfiguration und Feature-Flags.",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <section
      aria-label="KI-gestützte Gap-Analyse"
      className={CH_CARD}
      data-testid="cross-reg-llm-gap-panel"
    >
      <p className={CH_SECTION_LABEL}>KI-gestützte Gap-Analyse</p>
      <p className="mt-1 max-w-3xl text-sm text-slate-600">
        Priorisierte Control- und Maßnahmenvorschläge auf Basis Ihrer aktuellen Framework-Abdeckung
        (Metadaten only, keine Rechtsberatung).
      </p>

      <div className="mt-4 flex flex-wrap items-end gap-3">
        <label className="flex flex-col text-xs font-semibold text-slate-600">
          Fokus
          <select
            className="mt-1 rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-sm"
            value={focus}
            onChange={(e) => setFocus(e.target.value as FocusPreset)}
            data-testid="llm-gap-focus"
            disabled={busy}
          >
            {FOCUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className={`${CH_BTN_PRIMARY} text-sm`}
          onClick={() => void runAnalysis()}
          disabled={busy}
          data-testid="llm-gap-analyze"
        >
          {busy ? "Analyse läuft…" : "Gaps analysieren (KI)"}
        </button>
      </div>

      {busy ? (
        <p className="mt-4 text-sm text-slate-600" role="status">
          <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-cyan-600 border-t-transparent align-middle" />{" "}
          Auswertung Ihrer aktuellen Framework-Abdeckung…
        </p>
      ) : null}

      {err ? (
        <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50/80 p-3 text-sm text-rose-900">
          <p>{err}</p>
          <button
            type="button"
            className={`${CH_BTN_SECONDARY} mt-2 text-xs`}
            onClick={() => void runAnalysis()}
          >
            Erneut versuchen
          </button>
        </div>
      ) : null}

      {suggestions.length > 0 ? (
        <ul className="mt-6 space-y-3" data-testid="llm-gap-suggestions">
          {suggestions.map((s, i) => {
            const expanded = openIdx === i;
            return (
              <li
                key={`${s.suggested_control_name}-${i}`}
                className="rounded-xl border border-slate-200 bg-white shadow-sm"
              >
                <button
                  type="button"
                  className="flex w-full items-start justify-between gap-2 px-4 py-3 text-left"
                  onClick={() => setOpenIdx(expanded ? null : i)}
                  aria-expanded={expanded}
                >
                  <div>
                    <p className="font-semibold text-slate-900">{s.suggested_control_name}</p>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {s.frameworks.map((fk) => (
                        <span
                          key={fk}
                          className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-700"
                        >
                          {badgeFramework(fk)}
                        </span>
                      ))}
                      <span className="rounded-full bg-cyan-50 px-2 py-0.5 text-[10px] font-semibold text-cyan-900">
                        {s.requirement_ids.length} Pflichten
                      </span>
                      <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-900">
                        {s.priority}
                      </span>
                    </div>
                  </div>
                  <span className="text-xs text-slate-500">{expanded ? "▲" : "▼"}</span>
                </button>
                {expanded ? (
                  <div className="border-t border-slate-100 px-4 py-3 text-sm text-slate-700">
                    {s.rationale ? <p className="text-slate-600">{s.rationale}</p> : null}
                    <p className="mt-2 text-xs font-semibold uppercase text-slate-500">
                      Vorschlag Control
                    </p>
                    <p className="mt-1 whitespace-pre-wrap">{s.suggested_control_description}</p>
                    <p className="mt-2 text-xs text-slate-500">
                      Typ: {s.recommendation_type} · Rolle: {s.suggested_owner_role}
                    </p>
                    <p className="mt-3 text-xs font-semibold uppercase text-slate-500">
                      Betroffene Pflichten
                    </p>
                    <ul className="mt-1 list-inside list-disc text-xs text-slate-600">
                      {requirementLines(s, reqById).map((line) => (
                        <li key={`${line.code}-${line.title}`}>
                          {line.code} – {line.title}
                        </li>
                      ))}
                    </ul>
                    {s.suggested_actions.length > 0 ? (
                      <>
                        <p className="mt-3 text-xs font-semibold uppercase text-slate-500">
                          Vorgeschlagene Schritte
                        </p>
                        <ul className="mt-1 list-inside list-decimal text-xs text-slate-600">
                          {s.suggested_actions.map((a, j) => (
                            <li key={j}>{a}</li>
                          ))}
                        </ul>
                      </>
                    ) : null}
                    <div className="mt-4 flex flex-wrap gap-2">
                      <button
                        type="button"
                        className={`${CH_BTN_PRIMARY} text-xs`}
                        onClick={() =>
                          setControlDraft({
                            name: s.suggested_control_name,
                            description: s.suggested_control_description,
                          })
                        }
                      >
                        Control anlegen
                      </button>
                      <Link
                        href="/tenant/ai-governance-playbook"
                        className={`${CH_BTN_SECONDARY} inline-flex items-center text-xs no-underline`}
                      >
                        Zum AI Governance Playbook
                      </Link>
                    </div>
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      ) : null}

      {controlDraft ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="control-draft-title"
        >
          <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl bg-white p-5 shadow-xl">
            <h2 id="control-draft-title" className="text-lg font-bold text-slate-900">
              Control anlegen (Entwurf)
            </h2>
            <p className="mt-2 text-xs text-slate-600">
              Vorbefüllt aus KI-Vorschlag. Persistierung erfolgt über Ihre Compliance-Prozesse /
              Backend (z. B. <code className="rounded bg-slate-100 px-1">compliance_controls</code>).
            </p>
            <label className="mt-4 block text-xs font-semibold text-slate-600">
              Name
              <input
                className="mt-1 w-full rounded-lg border border-slate-200 px-2 py-2 text-sm"
                value={controlDraft.name}
                onChange={(e) => setControlDraft({ ...controlDraft, name: e.target.value })}
              />
            </label>
            <label className="mt-3 block text-xs font-semibold text-slate-600">
              Beschreibung
              <textarea
                className="mt-1 min-h-[120px] w-full rounded-lg border border-slate-200 px-2 py-2 text-sm"
                value={controlDraft.description}
                onChange={(e) => setControlDraft({ ...controlDraft, description: e.target.value })}
              />
            </label>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                className={`${CH_BTN_SECONDARY} text-xs`}
                onClick={() => setControlDraft(null)}
              >
                Schließen
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
