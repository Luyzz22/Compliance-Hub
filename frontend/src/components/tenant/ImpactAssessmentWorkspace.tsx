"use client";

import { useCallback, useState } from "react";

import { ImpactAssessmentEditor } from "@/components/tenant/ImpactAssessmentEditor";
import {
  fetchAIImpactAssessmentPortfolio,
  type AIImpactAssessmentPortfolioResponseDto,
  type AIImpactAssessmentSystemRowDto,
} from "@/lib/api";
import { CH_BADGE, CH_CARD, CH_SECTION_LABEL } from "@/lib/boardLayout";

type ImpactAssessmentWorkspaceProps = {
  tenantId: string;
  initialData: AIImpactAssessmentPortfolioResponseDto;
};

const POSTURE_LABELS: Record<string, string> = {
  no_ai_systems: "Kein System im Register",
  scope_incomplete: "Scope offen",
  consultation_gate: "Konsultations-Gate",
  review_overdue: "Review überfällig",
  approved: "Intern freigegeben",
  remediation_required: "Abhilfe erforderlich",
  in_review: "In unabhängiger Prüfung",
  review_ready: "Review-bereit",
  draft: "In Bearbeitung",
  action_required: "Handlungsbedarf",
};

const DACH_DATE_TIME = new Intl.DateTimeFormat("de-DE", {
  dateStyle: "medium",
  timeStyle: "short",
  timeZone: "Europe/Berlin",
});

function postureClasses(posture: string): string {
  if (posture === "approved") return "bg-emerald-50 text-emerald-800 ring-emerald-200";
  if (
    posture === "review_overdue" ||
    posture === "consultation_gate" ||
    posture === "remediation_required"
  ) {
    return "bg-rose-50 text-rose-800 ring-rose-200";
  }
  if (posture === "scope_incomplete" || posture === "action_required") {
    return "bg-amber-50 text-amber-900 ring-amber-200";
  }
  return "bg-cyan-50 text-cyan-900 ring-cyan-200";
}

function StepMarker({
  index,
  label,
  state,
}: {
  index: number;
  label: string;
  state: "complete" | "current" | "open";
}) {
  const markerClass =
    state === "complete"
      ? "border-emerald-400 bg-emerald-400 text-slate-950"
      : state === "current"
        ? "border-white bg-white text-slate-950"
        : "border-slate-600 bg-transparent text-slate-400";
  return (
    <li className="flex min-w-0 items-center gap-3">
      <span
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border text-xs font-semibold ${markerClass}`}
        aria-hidden
      >
        {state === "complete" ? "✓" : index}
      </span>
      <span className={state === "open" ? "text-slate-500" : "text-white"}>{label}</span>
    </li>
  );
}

function workflowStates(selected: AIImpactAssessmentSystemRowDto | null) {
  if (!selected) return ["current", "open", "open", "open"] as const;
  const assessment = selected.assessment;
  const scopeResolved =
    assessment.dpia_scope !== "undetermined" && assessment.fria_scope !== "undetermined";
  const analysisReady = selected.readiness_score_pct >= 65;
  const inReview = ["in_review", "remediation_required", "approved"].includes(
    assessment.lifecycle_status,
  );
  const approved = assessment.lifecycle_status === "approved";
  return [
    scopeResolved ? "complete" : "current",
    analysisReady ? "complete" : scopeResolved ? "current" : "open",
    inReview ? "complete" : analysisReady ? "current" : "open",
    approved ? "complete" : inReview ? "current" : "open",
  ] as const;
}

export function ImpactAssessmentWorkspace({
  tenantId,
  initialData,
}: ImpactAssessmentWorkspaceProps) {
  const [data, setData] = useState(initialData);
  const [selectedSystemId, setSelectedSystemId] = useState(
    initialData.systems[0]?.ai_system_id ?? "",
  );
  const [refreshError, setRefreshError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setRefreshError(null);
    try {
      setData(await fetchAIImpactAssessmentPortfolio(tenantId));
    } catch (error) {
      setRefreshError(
        error instanceof Error
          ? error.message
          : "Assessment-Portfolio konnte nicht aktualisiert werden.",
      );
      throw error;
    }
  }, [tenantId]);

  const selected =
    data.systems.find((system) => system.ai_system_id === selectedSystemId) ??
    data.systems[0] ??
    null;
  const states = workflowStates(selected);

  return (
    <div className="space-y-8">
      <section
        className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 text-white shadow-sm"
        aria-labelledby="impact-decision-path-title"
      >
        <div className="grid gap-7 px-5 py-6 md:px-7 lg:grid-cols-[minmax(0,1fr)_13rem] lg:items-end">
          <div>
            <p className="text-xs font-semibold tracking-wide text-slate-400">Assessment-Akte</p>
            <h2 id="impact-decision-path-title" className="mt-2 text-xl font-semibold">
              Vom Scope zur verantworteten Freigabe
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">
              Jeder Schritt bleibt nachvollziehbar. Das System berechnet operative Vollständigkeit,
              trifft aber weder die rechtliche Pflichtentscheidung noch die Einsatzfreigabe.
            </p>
            <ol className="mt-6 grid gap-4 text-sm sm:grid-cols-2 xl:grid-cols-4">
              {[
                "Scope klären",
                "Auswirkungen bewerten",
                "Kontrollen belegen",
                "Unabhängig freigeben",
              ].map((label, index) => (
                <StepMarker
                  key={label}
                  index={index + 1}
                  label={label}
                  state={states[index]}
                />
              ))}
            </ol>
          </div>
          <div className="border-l border-slate-700 pl-5">
            <p className="text-xs font-semibold text-slate-400">Portfolio-Reife</p>
            <p className="mt-1 text-4xl font-semibold tabular-nums">
              {data.readiness_score_pct}%
            </p>
            <p className="mt-2 text-xs leading-5 text-slate-300">
              {POSTURE_LABELS[data.posture] ?? data.posture}
            </p>
          </div>
        </div>
      </section>

      <section className={CH_CARD} aria-labelledby="impact-portfolio-summary-title">
        <div className="flex flex-wrap items-baseline justify-between gap-3 border-b border-slate-200 pb-4">
          <div>
            <p className={CH_SECTION_LABEL}>Portfolio-Kontrollstand</p>
            <h2 id="impact-portfolio-summary-title" className="mt-1 text-lg font-semibold text-slate-950">
              Scope, Review und Konsultation
            </h2>
          </div>
          <p className="text-xs text-slate-500">
            Stand: {DACH_DATE_TIME.format(new Date(data.generated_at_utc))}
          </p>
        </div>
        <dl className="mt-1 divide-y divide-slate-200 lg:grid lg:grid-cols-4 lg:divide-x lg:divide-y-0">
          {[
            ["Systeme", data.summary.total_systems, "text-slate-950"],
            ["Scope offen", data.summary.scope_open_count, "text-amber-700"],
            ["In Review", data.summary.in_review_count, "text-cyan-800"],
            ["Intern freigegeben", data.summary.approved_count, "text-emerald-700"],
          ].map(([label, value, valueClass], index) => (
            <div key={String(label)} className={`flex items-center justify-between gap-4 py-4 lg:block lg:px-5 ${index === 0 ? "lg:pl-0" : ""}`}>
              <dt className="text-xs font-semibold text-slate-500">{label}</dt>
              <dd className={`text-2xl font-semibold tabular-nums ${valueClass}`}>{value}</dd>
            </div>
          ))}
        </dl>
        {(data.summary.high_residual_risk_count > 0 ||
          data.summary.consultation_open_count > 0 ||
          data.summary.overdue_review_count > 0) && (
          <div className="mt-2 flex flex-wrap gap-x-5 gap-y-2 border-t border-slate-200 pt-4 text-xs text-slate-600">
            <span>Hohes Residualrisiko: <strong>{data.summary.high_residual_risk_count}</strong></span>
            <span>Offenes Konsultations-Gate: <strong>{data.summary.consultation_open_count}</strong></span>
            <span>Review überfällig: <strong>{data.summary.overdue_review_count}</strong></span>
          </div>
        )}
      </section>

      {data.systems.length === 0 ? (
        <section className={CH_CARD}>
          <h2 className="text-lg font-semibold text-slate-950">Noch keine KI-Systeme vorhanden</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Legen Sie zuerst ein System im KI-System-Register an. Unregistrierte Systeme werden
            bewusst nicht automatisch bewertet oder als nicht anwendbar eingeordnet.
          </p>
        </section>
      ) : (
        <section className="grid gap-5 xl:grid-cols-[20rem_minmax(0,1fr)]" aria-label="Impact Assessments">
          <aside className={`${CH_CARD} h-fit xl:sticky xl:top-28`}>
            <p className={CH_SECTION_LABEL}>Systemportfolio</p>
            <label className="mt-4 block text-xs font-semibold text-slate-700 xl:hidden" htmlFor="impact-system-select">
              KI-System auswählen
            </label>
            <select
              id="impact-system-select"
              className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 xl:hidden"
              value={selected?.ai_system_id ?? ""}
              onChange={(event) => setSelectedSystemId(event.target.value)}
            >
              {data.systems.map((system) => (
                <option key={system.ai_system_id} value={system.ai_system_id}>
                  {system.ai_system_name}
                </option>
              ))}
            </select>
            <ul className="mt-4 hidden space-y-2 xl:block">
              {data.systems.map((system) => {
                const active = system.ai_system_id === selected?.ai_system_id;
                return (
                  <li key={system.ai_system_id}>
                    <button
                      type="button"
                      className={`min-h-14 w-full rounded-lg border px-3 py-3 text-left transition-colors ${
                        active
                          ? "border-slate-900 bg-slate-950 text-white"
                          : "border-slate-200 bg-white text-slate-800 hover:border-slate-300 hover:bg-slate-50"
                      }`}
                      onClick={() => setSelectedSystemId(system.ai_system_id)}
                      aria-pressed={active}
                    >
                      <span className="block truncate text-sm font-semibold">
                        {system.ai_system_name}
                      </span>
                      <span className={`mt-1 block text-xs ${active ? "text-slate-300" : "text-slate-500"}`}>
                        {system.readiness_score_pct}% · {POSTURE_LABELS[system.posture] ?? system.posture}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </aside>

          {selected ? (
            <div className="min-w-0 space-y-4">
              <section className={CH_CARD} aria-labelledby="selected-impact-system-title">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className={CH_SECTION_LABEL}>{selected.business_unit}</p>
                    <h2 id="selected-impact-system-title" className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">
                      {selected.ai_system_name}
                    </h2>
                    <p className="mt-1 text-xs text-slate-500">
                      {selected.ai_system_id} · {selected.ai_act_category} · {selected.risk_level}
                    </p>
                  </div>
                  <span className={`${CH_BADGE} ${postureClasses(selected.posture)}`}>
                    {POSTURE_LABELS[selected.posture] ?? selected.posture}
                  </span>
                </div>
                <div className="mt-5 grid gap-4 sm:grid-cols-[1fr_auto] sm:items-center">
                  <div>
                    <label htmlFor="impact-readiness-progress" className="text-xs font-semibold text-slate-700">
                      Dokumentationsreife {selected.readiness_score_pct}%
                    </label>
                    <progress
                      id="impact-readiness-progress"
                      className="mt-2 h-2 w-full overflow-hidden rounded-full accent-cyan-700"
                      value={selected.readiness_score_pct}
                      max={100}
                    >
                      {selected.readiness_score_pct}%
                    </progress>
                  </div>
                  <p className="text-xs text-slate-500">
                    {selected.reviewed_sections}/{selected.applicable_sections} Prüffelder reviewed
                  </p>
                </div>
                <div className="mt-4 flex flex-wrap gap-2 text-xs">
                  <span className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-slate-700">
                    Register-Signal DSFA: {selected.registry_dpia_signal ? "ja" : "nein"}
                  </span>
                  <span className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-slate-700">
                    Version v{selected.assessment.version}
                  </span>
                </div>
                {selected.blockers.length > 0 ? (
                  <div className="mt-5 border-l-2 border-amber-400 pl-4">
                    <p className="text-xs font-semibold text-slate-800">Offene Freigabe-Gates</p>
                    <ul className="mt-2 list-disc space-y-1 pl-4 text-xs leading-5 text-slate-600">
                      {selected.blockers.map((blocker) => (
                        <li key={blocker}>{blocker}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </section>

              <ImpactAssessmentEditor
                key={selected.ai_system_id}
                tenantId={tenantId}
                system={selected}
                onSaved={refresh}
              />
            </div>
          ) : null}
        </section>
      )}

      {refreshError ? (
        <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900">
          {refreshError}
        </p>
      ) : null}

      <section className="rounded-xl border border-slate-200 bg-slate-50 px-5 py-4 text-xs leading-5 text-slate-600">
        <p>{data.legal_disclaimer_de}</p>
        <div className="mt-2 flex flex-wrap gap-x-5 gap-y-2">
          <a className="font-semibold text-[var(--sbs-text-accent)] underline underline-offset-4" href={data.source_urls.gdpr} target="_blank" rel="noreferrer">
            Primärquelle: DSGVO Art. 35 und 36
          </a>
          <a className="font-semibold text-[var(--sbs-text-accent)] underline underline-offset-4" href={data.source_urls.eu_ai_act} target="_blank" rel="noreferrer">
            Primärquelle: EU AI Act Art. 27
          </a>
        </div>
      </section>
    </div>
  );
}
