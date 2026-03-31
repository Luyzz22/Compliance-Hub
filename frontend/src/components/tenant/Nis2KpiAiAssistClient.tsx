"use client";

import React, { useState } from "react";

import {
  postNis2KritisKpiSuggestions,
  upsertNis2KritisKpi,
  type Nis2KritisKpiSuggestion,
  type Nis2KritisKpiType,
} from "@/lib/api";
import { CH_BTN_PRIMARY, CH_BTN_SECONDARY } from "@/lib/boardLayout";
import { featureLlmEnabled, featureLlmKpiSuggestions } from "@/lib/config";

const KPI_LABEL: Record<string, string> = {
  INCIDENT_RESPONSE_MATURITY: "Incident-Readiness",
  SUPPLIER_RISK_COVERAGE: "Supplier-Risk",
  OT_IT_SEGREGATION: "OT/IT-Segregation",
};

type Props = {
  aiSystemId: string;
};

export function Nis2KpiAiAssistClient({ aiSystemId }: Props) {
  const enabled = featureLlmEnabled() && featureLlmKpiSuggestions();
  const [ctx, setCtx] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<Nis2KritisKpiSuggestion[] | null>(null);
  const [ignored, setIgnored] = useState<Record<string, boolean>>({});
  const [draftPct, setDraftPct] = useState<Partial<Record<Nis2KritisKpiType, number>>>({});
  const [saving, setSaving] = useState<Nis2KritisKpiType | null>(null);

  if (!enabled) return null;

  const fetchSuggestions = async () => {
    if (ctx.trim().length < 10) {
      setErr("Bitte mindestens 10 Zeichen Kontext eingeben.");
      return;
    }
    setLoading(true);
    setErr(null);
    try {
      const res = await postNis2KritisKpiSuggestions(aiSystemId, ctx.trim());
      setSuggestions(res.suggestions);
      setIgnored({});
      setDraftPct({});
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Anfrage fehlgeschlagen");
    } finally {
      setLoading(false);
    }
  };

  const applyOne = (s: Nis2KritisKpiSuggestion) => {
    setDraftPct((d) => ({ ...d, [s.kpi_type]: s.suggested_value_percent }));
    setIgnored((ig) => ({ ...ig, [s.kpi_type]: false }));
  };

  const ignoreOne = (k: Nis2KritisKpiType) => {
    setIgnored((ig) => ({ ...ig, [k]: true }));
    setDraftPct((d) => {
      const next = { ...d };
      delete next[k];
      return next;
    });
  };

  const saveOne = async (kpiType: Nis2KritisKpiType) => {
    const v = draftPct[kpiType];
    if (v === undefined) return;
    setSaving(kpiType);
    try {
      await upsertNis2KritisKpi(aiSystemId, {
        kpi_type: kpiType,
        value_percent: Math.min(100, Math.max(0, Math.round(v))),
        evidence_ref: "KI-Vorschlag (manuell bestätigt)",
        last_reviewed_at: new Date().toISOString(),
      });
      setIgnored((ig) => ({ ...ig, [kpiType]: true }));
      setDraftPct((d) => {
        const n = { ...d };
        delete n[kpiType];
        return n;
      });
    } finally {
      setSaving(null);
    }
  };

  return (
    <div className="mt-4 rounded-xl border border-dashed border-cyan-200 bg-cyan-50/40 p-4">
      <p className="text-xs font-semibold text-cyan-950">KI-Assistenz (NIS2 / KRITIS)</p>
      <p className="mt-1 text-xs text-slate-600">
        Nur Vorschläge – finale Bewertung und Speicherung durch das Compliance-Team.
      </p>
      <label className="mt-3 block text-xs font-medium text-slate-700">
        Kontext / Beschreibung
        <textarea
          className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900"
          rows={4}
          value={ctx}
          onChange={(e) => setCtx(e.target.value)}
          placeholder="Runbooks, Prozesse, Policies, Lieferantenregister, OT/IT-Trennung …"
        />
      </label>
      <button
        type="button"
        className={`${CH_BTN_PRIMARY} mt-3`}
        disabled={loading}
        onClick={() => void fetchSuggestions()}
      >
        {loading ? "Laden…" : "KI-Vorschlag holen"}
      </button>
      {err ? <p className="mt-2 text-sm text-red-700">{err}</p> : null}
      {suggestions && suggestions.length > 0 ? (
        <ul className="mt-4 space-y-3">
          {suggestions.map((s) => (
            <li
              key={s.kpi_type}
              className="rounded-lg border border-slate-200 bg-white p-3 text-sm"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-semibold text-slate-900">
                  {KPI_LABEL[s.kpi_type] ?? s.kpi_type}
                </span>
                <span className="text-xs text-slate-500">
                  Confidence {(s.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <p className="mt-2 text-slate-600">{s.rationale}</p>
              <p className="mt-2 tabular-nums text-lg font-semibold text-slate-900">
                Vorschlag: {s.suggested_value_percent}%
              </p>
              {draftPct[s.kpi_type] !== undefined && !ignored[s.kpi_type] ? (
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <label className="text-xs text-slate-600">
                    Wert vor Speichern anpassen
                    <input
                      type="number"
                      min={0}
                      max={100}
                      className="ml-2 w-20 rounded border border-slate-200 px-2 py-1"
                      value={draftPct[s.kpi_type] ?? 0}
                      onChange={(e) =>
                        setDraftPct((d) => ({
                          ...d,
                          [s.kpi_type]: Number(e.target.value),
                        }))
                      }
                    />
                  </label>
                  <button
                    type="button"
                    className={`${CH_BTN_PRIMARY} text-xs`}
                    disabled={saving === s.kpi_type}
                    onClick={() => void saveOne(s.kpi_type)}
                  >
                    {saving === s.kpi_type ? "Speichern…" : "KPI speichern"}
                  </button>
                </div>
              ) : null}
              <div className="mt-2 flex flex-wrap gap-2">
                <button
                  type="button"
                  className={`${CH_BTN_SECONDARY} text-xs`}
                  onClick={() => applyOne(s)}
                  disabled={ignored[s.kpi_type]}
                >
                  Wert übernehmen
                </button>
                <button
                  type="button"
                  className="text-xs text-slate-500 underline"
                  onClick={() => ignoreOne(s.kpi_type)}
                >
                  Ignorieren
                </button>
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
