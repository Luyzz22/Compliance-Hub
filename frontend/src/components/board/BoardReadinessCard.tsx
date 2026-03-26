"use client";

import React, { useCallback, useEffect, useState } from "react";

import {
  fetchTenantReadinessScore,
  postTenantReadinessScoreExplain,
  type ReadinessScoreResponseDto,
} from "@/lib/api";
import { CH_BTN_SECONDARY, CH_CARD, CH_SECTION_LABEL } from "@/lib/boardLayout";
import { featureLlmEnabled, featureLlmExplain, featureReadinessScore } from "@/lib/config";
import { openWorkspaceTenantAndGo } from "@/lib/workspaceTenantClient";

function scoreAccent(score: number): string {
  if (score < 40) return "text-rose-700";
  if (score < 70) return "text-amber-800";
  return "text-emerald-800";
}

function levelLabelDe(level: string): string {
  if (level === "basic") return "Basic";
  if (level === "managed") return "Managed";
  if (level === "embedded") return "Embedded";
  return level;
}

function DimBar({
  testId,
  label,
  value,
  hint,
}: {
  testId: string;
  label: string;
  value: number;
  /** Kurz-Tooltip (Board-tauglich, EU AI Act / ISO / NIS2-Kontext). */
  hint?: string;
}) {
  const v = Math.max(0, Math.min(100, value));
  return (
    <div className="mt-2" data-testid={testId}>
      <div className="flex justify-between text-[0.65rem] font-medium text-slate-600">
        <span title={hint}>{label}</span>
        <span className="tabular-nums text-slate-800">{v}</span>
      </div>
      <div className="mt-0.5 h-1.5 overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-cyan-600 transition-[width]"
          style={{ width: `${v}%` }}
        />
      </div>
    </div>
  );
}

export function BoardReadinessCard({
  tenantId,
  isDemoTenant = false,
}: {
  tenantId: string;
  /** Pilot/Seed-Mandant: kurzer Hinweis, dass der Score aus Demo-Daten stammt. */
  isDemoTenant?: boolean;
}) {
  const [data, setData] = useState<ReadinessScoreResponseDto | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(true);
  const [explainBusy, setExplainBusy] = useState(false);
  const [explain, setExplain] = useState<string | null>(null);
  const [explainErr, setExplainErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setBusy(true);
    setErr(null);
    try {
      const r = await fetchTenantReadinessScore(tenantId);
      setData(r);
    } catch (e) {
      setData(null);
      setErr(e instanceof Error ? e.message : "Readiness Score konnte nicht geladen werden");
    } finally {
      setBusy(false);
    }
  }, [tenantId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!featureReadinessScore()) {
    return null;
  }

  const runExplain = async () => {
    setExplainBusy(true);
    setExplainErr(null);
    setExplain(null);
    try {
      const r = await postTenantReadinessScoreExplain(tenantId);
      setExplain(r.explanation);
    } catch (e) {
      setExplainErr(e instanceof Error ? e.message : "KI-Erklärung fehlgeschlagen");
    } finally {
      setExplainBusy(false);
    }
  };

  const d = data?.dimensions;

  return (
    <article className={CH_CARD} data-testid="board-readiness-card">
      <p className={CH_SECTION_LABEL}>AI &amp; Compliance Readiness</p>
      {isDemoTenant ? (
        <p className="mt-1 text-xs leading-snug text-slate-500">
          <strong className="font-semibold text-slate-600">Demomandant</strong> – keine echten
          Betriebsdaten. Score = strukturelle Reife (EU AI Act, ISO 42001/27001, Nachweise). Nutzung
          der Plattform (GAI) und Laufzeit-Signale (OAMI) ergänzen das Bild im Board-Report bzw. in
          der Governance-Maturity-Auswertung.
        </p>
      ) : null}
      {busy && !data ? <p className="mt-2 text-sm text-slate-600">Lade Score…</p> : null}
      {err ? (
        <p className="mt-2 text-sm text-rose-800">{err}</p>
      ) : null}
      {data ? (
        <>
          <div className="mt-3 flex flex-wrap items-end gap-4">
            <div>
              <p
                className={`text-4xl font-bold tabular-nums tracking-tight ${scoreAccent(data.score)}`}
                data-testid="board-readiness-score-value"
              >
                {data.score}
                <span className="text-lg font-semibold text-slate-500">/100</span>
              </p>
              <p className="mt-1 text-sm font-medium text-slate-700">
                Level: <span className="text-slate-900">{levelLabelDe(data.level)}</span>
              </p>
            </div>
            <button
              type="button"
              className={`${CH_BTN_SECONDARY} text-xs`}
              onClick={() => void load()}
              disabled={busy}
            >
              Aktualisieren
            </button>
          </div>
          <p className="mt-3 text-sm leading-relaxed text-slate-700">{data.interpretation}</p>
          {d ? (
            <div className="mt-4 max-w-md border-t border-slate-100 pt-3">
              <p className="mb-1 text-[0.65rem] font-medium text-slate-500">
                Fünf Dimensionen (ohne einzelne KI-Laufzeit – die liefert OAMI separat)
              </p>
              <DimBar
                testId="readiness-dim-setup"
                label="Setup"
                value={d.setup.score_0_100}
                hint="AI-Governance-Wizard, Rollen, Framework-Scopes (u. a. ISO 42001-Anschluss)."
              />
              <DimBar
                testId="readiness-dim-coverage"
                label="Coverage"
                value={d.coverage.score_0_100}
                hint="Abdeckung EU AI Act, NIS2, ISO 27001/42001 im Compliance-Graphen."
              />
              <DimBar
                testId="readiness-dim-kpi"
                label="KPIs"
                value={d.kpi.score_0_100}
                hint="KPI-/KRI-Zeitreihen im KI-Register (Drift, Incidents, …)."
              />
              <DimBar
                testId="readiness-dim-gaps"
                label="Gaps"
                value={d.gaps.score_0_100}
                hint="Regulatorische Lücken – z. B. fehlende Controls zu EU-AI-Act-Pflichten."
              />
              <DimBar
                testId="readiness-dim-reporting"
                label="Reporting"
                value={d.reporting.score_0_100}
                hint="Board- und Management-Reports – Transparenz für Aufsichtsrat / GF."
              />
            </div>
          ) : null}
          <div className="mt-5 flex flex-wrap gap-2">
            <button
              type="button"
              className={`${CH_BTN_SECONDARY} text-xs`}
              onClick={() => openWorkspaceTenantAndGo(tenantId, "/tenant/ai-governance-playbook")}
            >
              Details: Playbook
            </button>
            <button
              type="button"
              className={`${CH_BTN_SECONDARY} text-xs`}
              onClick={() =>
                openWorkspaceTenantAndGo(tenantId, "/tenant/cross-regulation-dashboard")
              }
            >
              Cross-Regulation
            </button>
            <button
              type="button"
              className={`${CH_BTN_SECONDARY} text-xs`}
              onClick={() => openWorkspaceTenantAndGo(tenantId, "/board/kpis")}
            >
              Board-KPIs
            </button>
          </div>
          {featureLlmEnabled() && featureLlmExplain() ? (
            <div className="mt-4 border-t border-slate-100 pt-4">
              <button
                type="button"
                className={`${CH_BTN_SECONDARY} text-xs`}
                disabled={explainBusy}
                onClick={() => void runExplain()}
                data-testid="board-readiness-explain-btn"
              >
                {explainBusy ? "KI formuliert…" : "Score per KI erklären (Top-3-Maßnahmen)"}
              </button>
              {explainErr ? <p className="mt-2 text-sm text-rose-800">{explainErr}</p> : null}
              {explain ? (
                <p className="mt-3 whitespace-pre-wrap text-sm text-slate-700" data-testid="board-readiness-explain-text">
                  {explain}
                </p>
              ) : null}
            </div>
          ) : null}
        </>
      ) : null}
    </article>
  );
}
