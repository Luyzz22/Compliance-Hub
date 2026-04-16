"use client";

import Link from "next/link";

import type { TenantRiskOverview } from "@/lib/tenantRiskOverview";
import { nis2ExposureCategoryLabel } from "@/lib/tenantRiskOverview";
import { TENANT_AI_ACT_SELF_ASSESSMENTS_PATH } from "@/lib/aiActSelfAssessmentRoutes";
import { TENANT_NIS2_WIZARD_BASE } from "@/lib/nis2WizardRoutes";
import {
  CH_BTN_PRIMARY,
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_PAGE_NAV_LINK,
  CH_SECTION_LABEL,
} from "@/lib/boardLayout";

interface Props {
  overview: TenantRiskOverview;
}

function exposurePillClass(level: TenantRiskOverview["nis2ExposureLevel"]): string {
  if (level === "high") {
    return "bg-rose-100 text-rose-900 ring-rose-200/80";
  }
  if (level === "medium") {
    return "bg-amber-100 text-amber-950 ring-amber-200/80";
  }
  return "bg-emerald-100 text-emerald-900 ring-emerald-200/80";
}

/**
 * Zentrales Risk & Control Overview (Dummy-Daten aus fetchTenantRiskOverview).
 * TODO: Live-Daten vom Server; interaktive Filter; Drilldown in System-/Wizard-Views.
 */
export function TenantRiskOverviewPanel({ overview }: Props) {
  return (
    <div className="space-y-8 md:space-y-10">
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <article className={`${CH_CARD} border-slate-200/80`}>
          <p className={CH_SECTION_LABEL}>KI-Systeme</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-slate-900">
            {overview.aiSystemsTotal}
          </p>
          <p className="mt-1 text-xs text-slate-600">im Mandanten-Register erfasst</p>
        </article>
        <article className={`${CH_CARD} border-slate-200/80`}>
          <p className={CH_SECTION_LABEL}>AI Act · HIGH Risk</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-rose-700">
            {overview.aiHighRiskCount}
          </p>
          <p className="mt-1 text-xs text-slate-600">LIMITED: {overview.aiLimitedRiskCount}</p>
        </article>
        <article className={`${CH_CARD} border-slate-200/80`}>
          <p className={CH_SECTION_LABEL}>NIS2 / KRITIS · InScope</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-[var(--sbs-navy-deep)]">
            {overview.nis2InScopeScore}
          </p>
          <p className="mt-1 text-xs text-slate-600">
            Exposure:{" "}
            <span
              className={`inline-flex rounded-full px-2 py-0.5 text-[0.65rem] font-semibold ring-1 ring-inset ${exposurePillClass(overview.nis2ExposureLevel)}`}
            >
              {overview.nis2ExposureLevel}
            </span>
          </p>
        </article>
        <article className={`${CH_CARD} border-slate-200/80`}>
          <p className={CH_SECTION_LABEL}>Offene Maßnahmen</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-slate-900">
            {overview.aiActOpenActionsCount}
          </p>
          <p className="mt-1 text-xs text-slate-600">AI-Act / Self-Assessment (heuristisch)</p>
        </article>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>EU AI Act</p>
          <h2 className="mt-1 text-lg font-semibold text-slate-900">Risiko & Pflichten</h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-600">
            Übersicht nach Risikostufe (HIGH / LIMITED / MINIMAL) und Self-Assessment-Status.
            HIGH-Systeme erfordern u. a. stärkere Dokumentation, Logging und Post-Market
            Surveillance — Details im jeweiligen System- und Assessment-Run.
          </p>
          <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200/80">
            <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
              <thead className="bg-slate-50/90 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-3 py-2">System</th>
                  <th className="px-3 py-2">Risiko</th>
                  <th className="px-3 py-2">Self-Assessment</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {overview.topRiskAiSystems.map((row) => (
                  <tr key={row.ai_system_id} className="hover:bg-slate-50/80">
                    <td className="px-3 py-2 font-medium text-slate-900">{row.display_name}</td>
                    <td className="px-3 py-2 text-slate-800">{row.risk_level}</td>
                    <td className="px-3 py-2 text-slate-600">{row.self_assessment_status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link href={TENANT_AI_ACT_SELF_ASSESSMENTS_PATH} className={CH_BTN_PRIMARY}>
              Self-Assessments öffnen
            </Link>
            <Link href="/tenant/ai-systems" className={CH_BTN_SECONDARY}>
              KI-System-Register
            </Link>
          </div>
        </article>

        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>NIS2 / KRITIS (DACH)</p>
          <h2 className="mt-1 text-lg font-semibold text-slate-900">Exposure & Haftung</h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-600">
            InScope-Score und Kategorie sind indikativ (BSIG / KRITIS-Dachgesetz). Es gilt keine
            Übergangsfrist; persönliche Geschäftsleiterhaftung kann relevant sein — fachlich mit
            Legal/Kanzlei klären.
          </p>
          <dl className="mt-4 space-y-2 text-sm">
            <div className="flex justify-between gap-4 border-b border-slate-100 py-2">
              <dt className="text-slate-500">InScope-Score</dt>
              <dd className="font-semibold text-slate-900">{overview.nis2InScopeScore} / 100</dd>
            </div>
            <div className="flex justify-between gap-4 border-b border-slate-100 py-2">
              <dt className="text-slate-500">Kategorie</dt>
              <dd className="font-medium text-slate-900">
                {nis2ExposureCategoryLabel(overview.nis2ExposureCategory)}
              </dd>
            </div>
            <div className="flex justify-between gap-4 py-2">
              <dt className="text-slate-500">ISO / Controls (Block 2)</dt>
              <dd className="text-slate-800">
                umgesetzt {overview.isoControlsImplemented} · geplant {overview.isoControlsPlanned}
              </dd>
            </div>
          </dl>
          <div className="mt-6 flex flex-wrap gap-2">
            <Link href={TENANT_NIS2_WIZARD_BASE} className={CH_BTN_PRIMARY}>
              NIS2-Wizard öffnen
            </Link>
            <Link href="/board/nis2-kritis" className={CH_BTN_SECONDARY}>
              NIS2-Projekt / Board
            </Link>
          </div>
          <p className="mt-4 text-xs text-slate-500">
            TODO: Letzte Wizard-Session und Profil aus <code className="rounded bg-slate-100 px-1">nis2_profiles</code>{" "}
            anzeigen.
          </p>
        </article>
      </div>

      <article className={CH_CARD}>
        <p className={CH_SECTION_LABEL}>Priorisierte To-dos</p>
        <h2 className="mt-1 text-lg font-semibold text-slate-900">Aus dem Overview abgeleitet</h2>
        <ul className="mt-4 list-decimal space-y-2 pl-5 text-sm text-slate-700">
          {overview.derivedTodos.map((t) => (
            <li key={t}>{t}</li>
          ))}
        </ul>
        <p className="mt-4 text-xs text-slate-500">
          TODO: Regeln serverseitig versionieren; mit Audit-Trail und Verantwortlichen verknüpfen.
        </p>
        <Link href="/tenant/cross-regulation-dashboard" className={`${CH_PAGE_NAV_LINK} mt-3 inline-block`}>
          Cross-Regulation-Dashboard
        </Link>
      </article>
    </div>
  );
}
