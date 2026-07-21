"use client";

import { useCallback, useState } from "react";

import { TransparencyAssessmentEditor } from "@/components/tenant/TransparencyAssessmentEditor";
import {
  fetchAITransparencyAssurance,
  type AITransparencyAssuranceResponseDto,
  type AITransparencySystemRowDto,
} from "@/lib/api";
import { CH_BADGE, CH_CARD, CH_SECTION_LABEL } from "@/lib/boardLayout";

type TransparencyAssuranceWorkspaceProps = {
  tenantId: string;
  initialData: AITransparencyAssuranceResponseDto;
};

const POSTURE_LABELS: Record<string, string> = {
  no_ai_systems: "Kein System im Register",
  scope_incomplete: "Scope offen",
  requires_scope: "Scope offen",
  action_required: "Handlungsbedarf",
  remediation_active: "Umsetzung läuft",
  implementation_pending_verification: "Prüfung ausstehend",
  verified: "Evidenzgeprüft",
  review_overdue: "Review überfällig",
};

function postureClasses(posture: string): string {
  if (posture === "verified") return "bg-emerald-50 text-emerald-800 ring-emerald-200";
  if (posture === "review_overdue" || posture === "action_required") {
    return "bg-rose-50 text-rose-800 ring-rose-200";
  }
  if (posture === "scope_incomplete" || posture === "requires_scope") {
    return "bg-amber-50 text-amber-900 ring-amber-200";
  }
  return "bg-cyan-50 text-cyan-900 ring-cyan-200";
}

function deadlineLabel(days: number): string {
  if (days < 0) return `seit ${Math.abs(days)} Tagen anwendbar`;
  if (days === 0) return "ab heute anwendbar";
  return `in ${days} Tagen anwendbar`;
}

export function TransparencyAssuranceWorkspace({
  tenantId,
  initialData,
}: TransparencyAssuranceWorkspaceProps) {
  const [data, setData] = useState(initialData);
  const [selectedSystemId, setSelectedSystemId] = useState(
    initialData.systems[0]?.ai_system_id ?? "",
  );
  const [refreshError, setRefreshError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setRefreshError(null);
    try {
      setData(await fetchAITransparencyAssurance(tenantId));
    } catch (error) {
      setRefreshError(
        error instanceof Error ? error.message : "Assurance-Übersicht konnte nicht aktualisiert werden.",
      );
      throw error;
    }
  }, [tenantId]);

  const selected =
    data.systems.find((system) => system.ai_system_id === selectedSystemId) ??
    data.systems[0] ??
    null;

  return (
    <div className="space-y-8">
      <section
        className={`overflow-hidden ${CH_CARD}`}
        aria-labelledby="article-50-deadline-title"
      >
        <div className="grid gap-6 lg:grid-cols-[1fr_auto] lg:items-center">
          <div>
            <p className={CH_SECTION_LABEL}>Regulatory clock</p>
            <h2 id="article-50-deadline-title" className="mt-2 text-xl font-semibold text-slate-950">
              Art. 50 Transparenzpflichten: 2. August 2026
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              {deadlineLabel(data.days_until_application)}. Die Ansicht trennt Provider- und
              Deployer-Pflichten, dokumentiert jede Nichtanwendbarkeit und wertet nur belegte,
              unabhängig geprüfte Kontrollen als verifiziert.
            </p>
          </div>
          <div className="min-w-40 rounded-2xl bg-slate-950 px-5 py-4 text-white">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">
              Readiness
            </p>
            <p className="mt-1 text-4xl font-semibold tabular-nums">
              {data.readiness_score_pct}%
            </p>
            <p className="mt-1 text-xs text-slate-300">
              {POSTURE_LABELS[data.posture] ?? data.posture}
            </p>
          </div>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5" aria-label="Assurance-Kennzahlen">
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>KI-Systeme</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-slate-950">
            {data.summary.total_systems}
          </p>
        </article>
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Assessed</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-slate-950">
            {data.summary.assessed_systems}
          </p>
        </article>
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Scope offen</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-amber-700">
            {data.summary.requires_scope_count}
          </p>
        </article>
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Verifiziert</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-emerald-700">
            {data.summary.verified_systems}
          </p>
        </article>
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Review überfällig</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-rose-700">
            {data.summary.overdue_review_count}
          </p>
        </article>
      </section>

      {data.systems.length === 0 ? (
        <section className={CH_CARD}>
          <h2 className="text-lg font-semibold text-slate-950">Noch keine KI-Systeme vorhanden</h2>
          <p className="mt-2 text-sm text-slate-600">
            Legen Sie zuerst ein System im KI-System-Register an. Unregistrierte Systeme werden
            bewusst nicht als konform oder nicht anwendbar bewertet.
          </p>
        </section>
      ) : (
        <section className="grid gap-5 xl:grid-cols-[20rem_minmax(0,1fr)]" aria-label="System-Assessments">
          <aside className={`${CH_CARD} h-fit xl:sticky xl:top-28`}>
            <p className={CH_SECTION_LABEL}>Systemportfolio</p>
            <label className="mt-4 block text-xs font-semibold text-slate-700 xl:hidden" htmlFor="assurance-system-select">
              KI-System auswählen
            </label>
            <select
              id="assurance-system-select"
              className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 xl:hidden"
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
              {data.systems.map((system: AITransparencySystemRowDto) => {
                const active = system.ai_system_id === selected?.ai_system_id;
                return (
                  <li key={system.ai_system_id}>
                    <button
                      type="button"
                      className={`w-full rounded-xl border px-3 py-3 text-left transition ${
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
              <div className={CH_CARD}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className={CH_SECTION_LABEL}>{selected.business_unit}</p>
                    <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">
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
                    <label htmlFor="system-readiness-progress" className="text-xs font-semibold text-slate-700">
                      Kontrollreife {selected.readiness_score_pct}%
                    </label>
                    <progress
                      id="system-readiness-progress"
                      className="mt-2 h-2 w-full overflow-hidden rounded-full accent-emerald-600"
                      value={selected.readiness_score_pct}
                      max={100}
                    >
                      {selected.readiness_score_pct}%
                    </progress>
                  </div>
                  <p className="text-xs text-slate-500">
                    {selected.verified_controls}/{selected.applicable_controls} Kontrollen verifiziert
                  </p>
                </div>
              </div>

              <TransparencyAssessmentEditor
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
        <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900">
          {refreshError}
        </p>
      ) : null}

      <section className="rounded-2xl border border-slate-200 bg-slate-50 px-5 py-4 text-xs leading-5 text-slate-600">
        <p>{data.legal_disclaimer_de}</p>
        <a
          className="mt-2 inline-flex font-semibold text-[var(--sbs-text-accent)] underline underline-offset-4"
          href={data.source_url}
          target="_blank"
          rel="noreferrer"
        >
          Primärquelle: EU-Kommission, Art.-50-Leitlinien und FAQ
        </a>
      </section>
    </div>
  );
}
