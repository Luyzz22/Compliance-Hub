"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import React, { useCallback, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";

import {
  ADVISOR_ID_FROM_ENV,
  fetchAdvisorClientGovernanceSnapshot,
  fetchAdvisorTenantReadinessScore,
  postAdvisorGovernanceSnapshotMarkdown,
  type AdvisorClientGovernanceSnapshotDto,
  type ReadinessScoreDimensionsDto,
  type ReadinessScoreResponseDto,
} from "@/lib/api";
import {
  CH_BTN_PRIMARY,
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_SECTION_LABEL,
  CH_SHELL,
} from "@/lib/boardLayout";
import {
  featureAiComplianceBoardReport,
  featureGovernanceMaturity,
  featureReadinessScore,
} from "@/lib/config";
import {
  GAI_ADVISOR_DETAIL_EXTRA,
  GAI_FULL_NAME,
  GAI_REG_HINT_SHORT,
  GAI_TOOLTIP_C_LEVEL,
  getReadinessCopy,
  OAMI_ADVISOR_DETAIL_EXTRA,
  OAMI_DEMO_SIGNALS_NOTE,
  OAMI_FULL_NAME,
  OAMI_REG_HINT_SHORT,
  OAMI_SECTION_TITLE,
  OAMI_TOOLTIP_C_LEVEL,
  parseReadinessLevel,
  READINESS_ADVISOR_DETAIL_EXTRA,
  READINESS_PRODUCT_TITLE,
  READINESS_REG_HINT_SHORT,
  READINESS_TAGLINE,
  READINESS_TOOLTIP_C_LEVEL,
  indexLevelLabelDe,
  readinessLevelLabelDe,
} from "@/lib/governanceMaturityDeCopy";
import { openWorkspaceTenantAndGo } from "@/lib/workspaceTenantClient";

const mdComponents = {
  h2: (props: React.ComponentPropsWithoutRef<"h2">) => (
    <h2 className="mt-4 border-b border-slate-200 pb-1 text-base font-bold text-slate-900" {...props} />
  ),
  h3: (props: React.ComponentPropsWithoutRef<"h3">) => (
    <h3 className="mt-3 text-sm font-bold text-slate-800" {...props} />
  ),
  p: (props: React.ComponentPropsWithoutRef<"p">) => (
    <p className="mt-2 text-sm leading-relaxed text-slate-700" {...props} />
  ),
  ul: (props: React.ComponentPropsWithoutRef<"ul">) => (
    <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-slate-700" {...props} />
  ),
  li: (props: React.ComponentPropsWithoutRef<"li">) => <li className="pl-0.5" {...props} />,
};

function readinessRecommendations(d: ReadinessScoreDimensionsDto): string[] {
  const out: string[] = [];
  if (d.setup.score_0_100 < 60) {
    out.push(
      `AI-Governance-Setup-Wizard: fehlende Schritte abschließen (Setup-Dimension ${d.setup.score_0_100}/100).`,
    );
  }
  if (d.coverage.score_0_100 < 60) {
    out.push(
      "Framework-Coverage erhöhen (Cross-Regulation Dashboard, Controls und Evidenzen verknüpfen).",
    );
  }
  if (d.kpi.score_0_100 < 60) {
    out.push(
      "Mindestens zwei KPI-Zeitreihen pro High-Risk-System erfassen (AI-KPI/KRI-Register).",
    );
  }
  if (d.gaps.score_0_100 < 60) {
    out.push("Kritische regulatorische Gaps reduzieren (Gap-Assist-Empfehlungen priorisieren).");
  }
  if (d.reporting.score_0_100 < 60) {
    out.push("Board-/Advisor-Reports erstellen und Historie aufbauen.");
  }
  if (out.length === 0) {
    out.push("Niveau halten: KPI-Monitoring und regelmäßige Board-Reports beibehalten.");
  }
  return out.slice(0, 5);
}

export function AdvisorGovernanceSnapshotView({ clientTenantId }: { clientTenantId: string }) {
  const advisorId = ADVISOR_ID_FROM_ENV;
  const searchParams = useSearchParams();
  const highlightGovernanceMaturity = searchParams.get("highlight") === "governance-maturity";
  const [gmHighlightPulse, setGmHighlightPulse] = useState(false);
  const [snap, setSnap] = useState<AdvisorClientGovernanceSnapshotDto | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(true);
  const [mdBusy, setMdBusy] = useState(false);
  const [mdOut, setMdOut] = useState<string | null>(null);
  const [mdErr, setMdErr] = useState<string | null>(null);
  const [readiness, setReadiness] = useState<ReadinessScoreResponseDto | null>(null);

  const load = useCallback(async () => {
    if (!advisorId) return;
    setBusy(true);
    setErr(null);
    try {
      const s = await fetchAdvisorClientGovernanceSnapshot(advisorId, clientTenantId);
      setSnap(s);
    } catch (e) {
      setSnap(null);
      setErr(e instanceof Error ? e.message : "Snapshot konnte nicht geladen werden");
    } finally {
      setBusy(false);
    }
  }, [advisorId, clientTenantId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (
      !highlightGovernanceMaturity ||
      !featureGovernanceMaturity() ||
      !snap?.governance_maturity_advisor_brief
    ) {
      return;
    }
    const timer = window.setTimeout(() => {
      document.getElementById("governance-maturity-anchor")?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
      setGmHighlightPulse(true);
      window.setTimeout(() => setGmHighlightPulse(false), 4500);
    }, 350);
    return () => window.clearTimeout(timer);
  }, [highlightGovernanceMaturity, snap?.governance_maturity_advisor_brief]);

  const syncReadiness = useCallback(
    async (loaded: AdvisorClientGovernanceSnapshotDto | null) => {
      if (!featureReadinessScore() || !advisorId) {
        setReadiness(null);
        return;
      }
      if (!loaded) {
        setReadiness(null);
        return;
      }
      if (loaded.readiness) {
        setReadiness(loaded.readiness);
        return;
      }
      try {
        const r = await fetchAdvisorTenantReadinessScore(advisorId, clientTenantId);
        setReadiness(r);
      } catch {
        setReadiness(null);
      }
    },
    [advisorId, clientTenantId],
  );

  useEffect(() => {
    void syncReadiness(snap);
  }, [snap, syncReadiness]);

  const readinessLevelParsed = readiness ? parseReadinessLevel(readiness.level) : null;

  const genMd = async () => {
    if (!advisorId) return;
    setMdBusy(true);
    setMdErr(null);
    setMdOut(null);
    try {
      const r = await postAdvisorGovernanceSnapshotMarkdown(advisorId, clientTenantId);
      setMdOut(r.markdown);
    } catch (e) {
      setMdErr(e instanceof Error ? e.message : "KI-Export fehlgeschlagen");
    } finally {
      setMdBusy(false);
    }
  };

  if (!advisorId) {
    return (
      <div className={CH_SHELL}>
        <p className="text-sm text-rose-800">Kein Berater konfiguriert (NEXT_PUBLIC_ADVISOR_ID).</p>
      </div>
    );
  }

  return (
    <div className={CH_SHELL} data-testid="advisor-governance-snapshot-view">
      <header className="mb-8">
        <p className="text-[0.7rem] font-bold uppercase tracking-[0.14em] text-cyan-800">Berater</p>
        <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-900">
          Mandanten-Governance-Snapshot
        </h1>
        <p className="mt-2 font-mono text-sm text-slate-600">{clientTenantId}</p>
        <div className="mt-3 max-w-3xl space-y-2 text-sm leading-relaxed text-slate-600">
          <p title={READINESS_TOOLTIP_C_LEVEL}>
            <span className="font-semibold text-slate-800">{READINESS_PRODUCT_TITLE}:</span>{" "}
            {READINESS_TAGLINE}
          </p>
          <p title={GAI_TOOLTIP_C_LEVEL}>
            <span className="font-semibold text-slate-800">{GAI_FULL_NAME}:</span>{" "}
            {GAI_TOOLTIP_C_LEVEL} {GAI_ADVISOR_DETAIL_EXTRA}
          </p>
          <p className="text-xs text-slate-500">{GAI_REG_HINT_SHORT}</p>
          <p title={OAMI_TOOLTIP_C_LEVEL}>
            <span className="font-semibold text-slate-800">{OAMI_FULL_NAME}:</span>{" "}
            {OAMI_TOOLTIP_C_LEVEL} {OAMI_ADVISOR_DETAIL_EXTRA}
          </p>
          <p className="text-xs text-slate-500">{OAMI_REG_HINT_SHORT}</p>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Link href="/advisor" className={`${CH_BTN_SECONDARY} text-xs no-underline`}>
            Zurück zum Portfolio
          </Link>
          <button
            type="button"
            className={`${CH_BTN_PRIMARY} text-xs`}
            disabled={busy}
            onClick={() => void load()}
          >
            Aktualisieren
          </button>
        </div>
      </header>

      {err ? (
        <div className="mb-6 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900">
          {err}
        </div>
      ) : null}

      {busy && !snap ? (
        <p className="text-sm text-slate-600">Lade Snapshot…</p>
      ) : null}

      {snap ? (
        <div className="space-y-6">
          <section className={CH_CARD} data-testid="snap-client-info">
            <p className={CH_SECTION_LABEL}>Mandant &amp; Scope</p>
            <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-xs font-semibold text-slate-500">Anzeigename</dt>
                <dd className="font-medium text-slate-900">{snap.client_info.display_name}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold text-slate-500">Branche / Land</dt>
                <dd className="text-slate-800">
                  {[snap.client_info.industry, snap.client_info.country].filter(Boolean).join(" · ") ||
                    "–"}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-semibold text-slate-500">Tenant-Typ (Wizard)</dt>
                <dd className="text-slate-800">{snap.client_info.tenant_kind ?? "–"}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold text-slate-500">Aktive Frameworks</dt>
                <dd className="flex flex-wrap gap-1">
                  {snap.framework_scope.active_frameworks.length ? (
                    snap.framework_scope.active_frameworks.map((k) => (
                      <span
                        key={k}
                        className="rounded-full bg-cyan-50 px-2 py-0.5 text-xs font-semibold text-cyan-900"
                      >
                        {k}
                      </span>
                    ))
                  ) : (
                    <span className="text-slate-500">–</span>
                  )}
                </dd>
              </div>
            </dl>
          </section>

          {featureReadinessScore() && readiness ? (
            <section className={CH_CARD} data-testid="snap-readiness">
              <p className={CH_SECTION_LABEL} title={READINESS_TOOLTIP_C_LEVEL}>
                {READINESS_PRODUCT_TITLE}
              </p>
              <p className="mt-1 text-xs text-slate-500">{READINESS_ADVISOR_DETAIL_EXTRA}</p>
              <p className="mt-1 text-[0.65rem] text-slate-500">{READINESS_REG_HINT_SHORT}</p>
              <p className="mt-2 text-sm text-slate-700">{readiness.interpretation}</p>
              <p className="mt-3 text-3xl font-bold tabular-nums text-slate-900">
                <span className={readiness.score < 40 ? "text-rose-700" : readiness.score < 70 ? "text-amber-800" : "text-emerald-800"}>
                  {readiness.score}
                </span>
                <span className="text-lg font-semibold text-slate-500">/100</span>
                <span
                  className="ml-2 text-base font-medium text-slate-600"
                  title={
                    readinessLevelParsed
                      ? getReadinessCopy(readinessLevelParsed).levelWithRegTooltip
                      : READINESS_REG_HINT_SHORT
                  }
                >
                  ({readinessLevelLabelDe(readiness.level)})
                </span>
              </p>
              <ul className="mt-3 grid gap-1 text-xs text-slate-600 sm:grid-cols-2">
                <li>Setup: {readiness.dimensions.setup.score_0_100}</li>
                <li>Coverage: {readiness.dimensions.coverage.score_0_100}</li>
                <li>KPIs: {readiness.dimensions.kpi.score_0_100}</li>
                <li>Gaps: {readiness.dimensions.gaps.score_0_100}</li>
                <li>Reporting: {readiness.dimensions.reporting.score_0_100}</li>
              </ul>
              <p className={`${CH_SECTION_LABEL} mt-4`}>Empfohlene Maßnahmen</p>
              <ul className="mt-2 list-inside list-disc text-sm text-slate-700">
                {readinessRecommendations(readiness.dimensions).map((line, i) => (
                  <li key={i}>{line}</li>
                ))}
              </ul>
            </section>
          ) : null}

          {featureGovernanceMaturity() && snap.governance_maturity_advisor_brief ? (
            <section
              id="governance-maturity-anchor"
              className={`${CH_CARD} ${
                gmHighlightPulse ? "ring-2 ring-cyan-500 ring-offset-2 transition-shadow" : ""
              }`}
              data-testid="snap-gm-advisor-brief"
            >
              <p className={CH_SECTION_LABEL}>Governance-Maturity-Brief</p>
              <p className="mt-1 text-xs text-slate-500">
                Strukturierte Kurzfassung für Triaging und Mandantenkommunikation (gleiche
                API-Enums wie Board-Kern).
              </p>
              {(() => {
                const gb = snap.governance_maturity_advisor_brief;
                const oa = gb.governance_maturity_summary.overall_assessment;
                return (
                  <>
                    <p className="mt-3 text-sm text-slate-800">
                      <span className="font-semibold">Gesamtbild (konservativ):</span>{" "}
                      {indexLevelLabelDe(oa.level)} ({oa.level})
                    </p>
                    <p className="mt-2 text-sm text-slate-700">{oa.short_summary}</p>
                    <p className={`${CH_SECTION_LABEL} mt-4`}>Fokusbereiche</p>
                    <ul className="mt-2 list-inside list-disc text-sm text-slate-700">
                      {gb.recommended_focus_areas.slice(0, 5).map((line, i) => (
                        <li key={i}>{line}</li>
                      ))}
                    </ul>
                    <p className="mt-3 text-sm text-slate-700">
                      <span className="font-semibold">Nächste Schritte (Horizont):</span>{" "}
                      {gb.suggested_next_steps_window}
                    </p>
                    {gb.client_ready_paragraph_de ? (
                      <p className="mt-3 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800">
                        {gb.client_ready_paragraph_de}
                      </p>
                    ) : null}
                  </>
                );
              })()}
            </section>
          ) : null}

          <section className={CH_CARD} data-testid="snap-gai-note">
            <p className={CH_SECTION_LABEL} title={GAI_TOOLTIP_C_LEVEL}>
              {GAI_FULL_NAME}
            </p>
            <p className="mt-1 text-sm text-slate-700">{GAI_TOOLTIP_C_LEVEL}</p>
            <p className="mt-1 text-xs text-slate-600">{GAI_ADVISOR_DETAIL_EXTRA}</p>
            <p className="mt-2 text-[0.65rem] text-slate-500">{GAI_REG_HINT_SHORT}</p>
            <p className="mt-2 text-xs text-slate-600">
              Kennzahl und Verlauf (0–100, z. B. 90 Tage) siehe API{" "}
              <span className="font-mono text-[0.7rem]">GET …/governance-maturity</span> – Feld{" "}
              <span className="font-mono text-[0.7rem]">governance_activity</span>.
            </p>
          </section>

          {snap.operational_ai_monitoring &&
          (snap.operational_ai_monitoring.systems_scored > 0 ||
            (snap.operational_ai_monitoring.narrative_de &&
              snap.operational_ai_monitoring.narrative_de.length > 0) ||
            snap.operational_ai_monitoring.index_90d != null) ? (
            <section className={CH_CARD} data-testid="snap-oami">
              <p className={CH_SECTION_LABEL} title={OAMI_TOOLTIP_C_LEVEL}>
                {OAMI_SECTION_TITLE}
              </p>
              <p className="mt-1 text-xs text-slate-600">{OAMI_TOOLTIP_C_LEVEL}</p>
              <p className="mt-1 text-xs text-slate-600">{OAMI_ADVISOR_DETAIL_EXTRA}</p>
              <p className="mt-1 text-[0.65rem] text-slate-500">{OAMI_REG_HINT_SHORT}</p>
              <p className="mt-1 text-xs text-slate-500">{OAMI_DEMO_SIGNALS_NOTE}</p>
              <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-xs font-semibold text-slate-500">Index / Level</dt>
                  <dd className="font-medium text-slate-900">
                    {snap.operational_ai_monitoring.index_90d ?? "–"}{" "}
                    <span className="text-slate-500">
                      / 100 · {indexLevelLabelDe(snap.operational_ai_monitoring.level)}
                    </span>
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-slate-500">Systeme mit Daten</dt>
                  <dd className="tabular-nums text-slate-800">
                    {snap.operational_ai_monitoring.systems_scored}
                  </dd>
                </div>
              </dl>
              {(snap.operational_ai_monitoring.safety_related_runtime_incidents_90d ?? 0) > 0 ||
              (snap.operational_ai_monitoring.availability_runtime_incidents_90d ?? 0) > 0 ||
              snap.operational_ai_monitoring.operational_subtype_hint_de ? (
                <div
                  className="mt-3 rounded-md border border-slate-100 bg-slate-50/80 px-3 py-2 text-xs text-slate-700"
                  data-testid="snap-oami-subtype"
                >
                  <p className="font-semibold text-slate-800">Laufzeit-Incidents nach Subtype (90 Tage)</p>
                  <p className="mt-1 tabular-nums">
                    Sicherheits-Subtype:{" "}
                    {snap.operational_ai_monitoring.safety_related_runtime_incidents_90d ?? 0}
                    <span className="mx-2 text-slate-300">|</span>
                    Verfügbarkeit:{" "}
                    {snap.operational_ai_monitoring.availability_runtime_incidents_90d ?? 0}
                  </p>
                  {snap.operational_ai_monitoring.operational_subtype_hint_de ? (
                    <p className="mt-2 text-slate-600">
                      {snap.operational_ai_monitoring.operational_subtype_hint_de}
                    </p>
                  ) : null}
                </div>
              ) : null}
              {snap.operational_ai_monitoring.narrative_de ? (
                <p className="mt-3 text-sm text-slate-700">{snap.operational_ai_monitoring.narrative_de}</p>
              ) : null}
              {snap.operational_ai_monitoring.drivers_de?.length ? (
                <div className="mt-3">
                  <p className={CH_SECTION_LABEL}>Treiber</p>
                  <ul className="mt-1 list-inside list-disc text-sm text-slate-700">
                    {snap.operational_ai_monitoring.drivers_de.map((line, i) => (
                      <li key={i}>{line}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </section>
          ) : null}

          <section className={CH_CARD} data-testid="snap-setup">
            <p className={CH_SECTION_LABEL}>AI Governance Setup &amp; Playbook</p>
            <p className="mt-2 text-sm text-slate-700">
              Guided Setup: {snap.setup_status.guided_setup_completed_steps}/
              {snap.setup_status.guided_setup_total_steps} Schritte · Wizard-Fortschritt:{" "}
              {snap.setup_status.ai_governance_wizard_progress_steps.length}/
              {snap.setup_status.ai_governance_wizard_steps_total} markierte Meilensteine
            </p>
          </section>

          <section className={CH_CARD} data-testid="snap-ai-systems">
            <p className={CH_SECTION_LABEL}>AI-Systeme &amp; High-Risk</p>
            <ul className="mt-2 list-inside list-disc text-sm text-slate-700">
              <li>Gesamt: {snap.ai_systems_summary.total_count}</li>
              <li>High-Risk: {snap.ai_systems_summary.high_risk_count}</li>
              <li>NIS2-kritisch (criticality very_high): {snap.ai_systems_summary.nis2_critical_count}</li>
            </ul>
          </section>

          <section className={CH_CARD} data-testid="snap-kpis">
            <p className={CH_SECTION_LABEL}>AI KPIs &amp; Monitoring</p>
            <ul className="mt-2 list-inside list-disc text-sm text-slate-700">
              <li>High-Risk-Systeme im KPI-Scope: {snap.kpi_summary.high_risk_systems_in_scope}</li>
              <li>Systeme mit KPI-Werten (Proxy): {snap.kpi_summary.systems_with_kpi_values}</li>
              <li>Kritische KPI-Zeilen: {snap.kpi_summary.critical_kpi_system_rows}</li>
              <li>Trends sichtbar (KPI-Definitionen): {snap.kpi_summary.aggregate_trends_non_flat}</li>
            </ul>
          </section>

          <section className={CH_CARD} data-testid="snap-cross-reg">
            <p className={CH_SECTION_LABEL}>Framework-Coverage &amp; Gaps</p>
            <p className="mt-1 text-xs text-slate-500">
              Regulatorische Gap-Positionen: {snap.gap_assist.regulatory_gap_items_count}
            </p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-[480px] w-full border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-xs uppercase text-slate-500">
                    <th className="py-2 pr-3">Framework</th>
                    <th className="py-2 pr-3">Coverage</th>
                    <th className="py-2">Gaps</th>
                  </tr>
                </thead>
                <tbody>
                  {snap.cross_reg_summary.map((f) => (
                    <tr key={f.framework_key} className="border-b border-slate-100">
                      <td className="py-2 pr-3 font-medium text-slate-900">{f.name}</td>
                      <td className="py-2 pr-3 tabular-nums">{f.coverage_percent}%</td>
                      <td className="py-2 tabular-nums">{f.gap_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className={CH_CARD} data-testid="snap-reports">
            <p className={CH_SECTION_LABEL}>Board- / Advisor-Reports</p>
            <p className="mt-2 text-sm text-slate-700">
              Anzahl Reports: {snap.reports_summary.reports_total}
              {snap.reports_summary.last_report_created_at ? (
                <>
                  {" "}
                  · zuletzt: {snap.reports_summary.last_report_created_at.slice(0, 10)} (
                  {snap.reports_summary.last_report_audience ?? "?"})
                </>
              ) : null}
            </p>
            {featureAiComplianceBoardReport() ? (
              <button
                type="button"
                className={`${CH_BTN_SECONDARY} mt-3 text-xs`}
                onClick={() =>
                  openWorkspaceTenantAndGo(clientTenantId, "/board/ai-compliance-report")
                }
              >
                Demo-Board-Report / Workspace öffnen
              </button>
            ) : null}
          </section>

          <section className={CH_CARD} data-testid="snap-actions">
            <p className={CH_SECTION_LABEL}>Aktionen</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                className={`${CH_BTN_PRIMARY} text-xs`}
                disabled={mdBusy}
                onClick={() => void genMd()}
                data-testid="snap-gen-md"
              >
                {mdBusy ? "KI generiert…" : "Snapshot als Markdown generieren (KI)"}
              </button>
              <button
                type="button"
                className={`${CH_BTN_SECONDARY} text-xs`}
                onClick={() => openWorkspaceTenantAndGo(clientTenantId, "/tenant/ai-governance-setup")}
              >
                AI Governance Setup Wizard öffnen
              </button>
              <button
                type="button"
                className={`${CH_BTN_SECONDARY} text-xs`}
                onClick={() =>
                  openWorkspaceTenantAndGo(clientTenantId, "/tenant/cross-regulation-dashboard")
                }
              >
                Cross-Regulation Dashboard öffnen
              </button>
            </div>
            {mdErr ? (
              <p className="mt-3 text-sm text-rose-800">{mdErr}</p>
            ) : null}
            {mdOut ? (
              <div
                className="mt-4 rounded-lg border border-slate-200 bg-white p-4 text-sm"
                data-testid="snap-md-preview"
              >
                <ReactMarkdown components={mdComponents}>{mdOut}</ReactMarkdown>
              </div>
            ) : null}
          </section>
        </div>
      ) : null}
    </div>
  );
}
