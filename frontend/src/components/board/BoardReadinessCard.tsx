"use client";

import React, { useCallback, useEffect, useState } from "react";

import {
  fetchTenantReadinessScore,
  postTenantReadinessScoreExplain,
  type ReadinessScoreExplainResponseDto,
  type ReadinessScoreResponseDto,
} from "@/lib/api";
import { CH_BTN_SECONDARY, CH_CARD, CH_SECTION_LABEL } from "@/lib/boardLayout";
import { featureLlmEnabled, featureLlmExplain, featureReadinessScore } from "@/lib/config";
import {
  DEMO_HINT_READINESS_CARD,
  OAMI_FULL_NAME,
  getReadinessCopy,
  parseReadinessLevel,
  READINESS_DIM_COVERAGE,
  READINESS_DIM_COVERAGE_HINT,
  READINESS_DIM_GAPS,
  READINESS_DIM_GAPS_HINT,
  READINESS_DIM_KPIS,
  READINESS_DIM_KPIS_HINT,
  READINESS_DIM_REPORTING,
  READINESS_DIM_REPORTING_HINT,
  READINESS_DIM_SETUP,
  READINESS_DIM_SETUP_HINT,
  READINESS_FIVE_DIMS_CAPTION,
  READINESS_LEVEL_ROW_LABEL,
  READINESS_PRODUCT_TITLE,
  READINESS_REG_HINT_SHORT,
  READINESS_TAGLINE,
  READINESS_TOOLTIP_C_LEVEL,
  readinessLevelLabelDe,
} from "@/lib/governanceMaturityDeCopy";
import { openWorkspaceTenantAndGo } from "@/lib/workspaceTenantClient";

function scoreAccent(score: number): string {
  if (score < 40) return "text-rose-700";
  if (score < 70) return "text-amber-800";
  return "text-emerald-800";
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
  /** Wenn gesetzt: kein initialer API-Fetch (z. B. Vitest). „Aktualisieren“ ruft weiterhin die API auf. */
  staticReadiness,
}: {
  tenantId: string;
  /** Pilot/Seed-Mandant: kurzer Hinweis, dass der Score aus Demo-Daten stammt. */
  isDemoTenant?: boolean;
  staticReadiness?: ReadinessScoreResponseDto;
}) {
  const staticMode = staticReadiness !== undefined;
  const [data, setData] = useState<ReadinessScoreResponseDto | null>(() =>
    staticMode ? staticReadiness : null,
  );
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(() => !staticMode);
  const [explainBusy, setExplainBusy] = useState(false);
  const [explainResult, setExplainResult] = useState<ReadinessScoreExplainResponseDto | null>(null);
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
    if (staticMode) {
      setData(staticReadiness);
      setBusy(false);
      setErr(null);
      return;
    }
    void load();
  }, [load, staticMode, staticReadiness]);

  if (!featureReadinessScore()) {
    return null;
  }

  const runExplain = async () => {
    setExplainBusy(true);
    setExplainErr(null);
    setExplainResult(null);
    try {
      const r = await postTenantReadinessScoreExplain(tenantId);
      setExplainResult(r);
    } catch (e) {
      setExplainErr(e instanceof Error ? e.message : "KI-Erklärung fehlgeschlagen");
    } finally {
      setExplainBusy(false);
    }
  };

  const d = data?.dimensions;
  const readinessLevelParsed = data ? parseReadinessLevel(data.level) : null;

  return (
    <article className={CH_CARD} data-testid="board-readiness-card">
      <p className={CH_SECTION_LABEL} title={READINESS_TOOLTIP_C_LEVEL}>
        {READINESS_PRODUCT_TITLE}
      </p>
      <p className="mt-1 text-xs leading-snug text-slate-600">{READINESS_TAGLINE}</p>
      <p className="mt-1 text-[0.65rem] leading-snug text-slate-500">{READINESS_REG_HINT_SHORT}</p>
      {isDemoTenant ? (
        <p className="mt-2 text-xs leading-snug text-amber-900/90">{DEMO_HINT_READINESS_CARD}</p>
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
                {READINESS_LEVEL_ROW_LABEL}{" "}
                <span
                  className="text-slate-900"
                  title={
                    readinessLevelParsed
                      ? getReadinessCopy(readinessLevelParsed).levelWithRegTooltip
                      : READINESS_REG_HINT_SHORT
                  }
                  data-testid="board-readiness-level-label"
                >
                  {readinessLevelLabelDe(data.level)}
                </span>
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
                {READINESS_FIVE_DIMS_CAPTION}
              </p>
              <DimBar
                testId="readiness-dim-setup"
                label={READINESS_DIM_SETUP}
                value={d.setup.score_0_100}
                hint={READINESS_DIM_SETUP_HINT}
              />
              <DimBar
                testId="readiness-dim-coverage"
                label={READINESS_DIM_COVERAGE}
                value={d.coverage.score_0_100}
                hint={READINESS_DIM_COVERAGE_HINT}
              />
              <DimBar
                testId="readiness-dim-kpi"
                label={READINESS_DIM_KPIS}
                value={d.kpi.score_0_100}
                hint={READINESS_DIM_KPIS_HINT}
              />
              <DimBar
                testId="readiness-dim-gaps"
                label={READINESS_DIM_GAPS}
                value={d.gaps.score_0_100}
                hint={READINESS_DIM_GAPS_HINT}
              />
              <DimBar
                testId="readiness-dim-reporting"
                label={READINESS_DIM_REPORTING}
                value={d.reporting.score_0_100}
                hint={READINESS_DIM_REPORTING_HINT}
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
              {explainResult ? (
                <div className="mt-3 space-y-2" data-testid="board-readiness-explain-block">
                  <p
                    className="whitespace-pre-wrap text-sm text-slate-700"
                    data-testid="board-readiness-explain-text"
                  >
                    {explainResult.explanation}
                  </p>
                  {explainResult.readiness_explanation?.regulatory_focus ? (
                    <p className="text-xs leading-snug text-slate-500">
                      {explainResult.readiness_explanation.regulatory_focus}
                    </p>
                  ) : null}
                  {explainResult.readiness_explanation &&
                  explainResult.readiness_explanation.drivers_positive.length > 0 ? (
                    <div>
                      <p className="text-[0.65rem] font-semibold uppercase tracking-wide text-slate-500">
                        Stärken
                      </p>
                      <ul className="mt-1 list-inside list-disc text-xs text-slate-600">
                        {explainResult.readiness_explanation.drivers_positive.map((line, i) => (
                          <li key={i}>{line}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  {explainResult.operational_monitoring_explanation &&
                  (explainResult.operational_monitoring_explanation.improvement_suggestions.length > 0 ||
                    explainResult.operational_monitoring_explanation.monitoring_gaps.length > 0 ||
                    (explainResult.operational_monitoring_explanation.safety_related_incidents_90d ??
                      0) > 0 ||
                    explainResult.operational_monitoring_explanation.oami_subtype_hint_de) ? (
                    <div className="border-t border-slate-100 pt-2">
                      <p className="text-[0.65rem] font-semibold text-slate-600">{OAMI_FULL_NAME}</p>
                      {explainResult.operational_monitoring_explanation.oami_subtype_hint_de ? (
                        <p
                          className="mt-1 text-xs leading-snug text-slate-600"
                          title="Sicherheitsnahe Laufzeit-Subtypen wirken stärker als reine Verfügbarkeit — ohne einzelne Gewichte."
                        >
                          {explainResult.operational_monitoring_explanation.oami_subtype_hint_de}
                        </p>
                      ) : null}
                      {(explainResult.operational_monitoring_explanation.safety_related_incidents_90d ??
                        0) > 0 ? (
                        <p className="mt-1 text-[0.65rem] text-slate-500">
                          Davon{" "}
                          <span className="font-semibold text-slate-700">
                            {explainResult.operational_monitoring_explanation.safety_related_incidents_90d}
                          </span>{" "}
                          sicherheitsrelevant (Laufzeit-Subtype).
                        </p>
                      ) : null}
                      {explainResult.operational_monitoring_explanation.improvement_suggestions.length > 0 ||
                      explainResult.operational_monitoring_explanation.monitoring_gaps.length > 0 ? (
                        <ul className="mt-1 list-inside list-disc text-xs text-slate-600">
                          {(
                            explainResult.operational_monitoring_explanation.improvement_suggestions.length
                              ? explainResult.operational_monitoring_explanation.improvement_suggestions
                              : explainResult.operational_monitoring_explanation.monitoring_gaps
                          ).map((line, i) => (
                            <li key={i}>{line}</li>
                          ))}
                        </ul>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>
          ) : null}
        </>
      ) : null}
    </article>
  );
}
