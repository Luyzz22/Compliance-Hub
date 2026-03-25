"use client";

import Link from "next/link";
import React, { useMemo, useState } from "react";

import {
  fetchRequirementControlsDetail,
  type CrossRegFrameworkSummaryDto,
  type RegulatoryControlRowDto,
  type RegulatoryRequirementRowDto,
  type RequirementControlsDetailResponseDto,
} from "@/lib/api";
import {
  CH_BTN_PRIMARY,
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_SECTION_LABEL,
} from "@/lib/boardLayout";

type FrameworkFilter = "all" | string;
type CoverageFilter = "all" | "gap" | "partial" | "full" | "planned_only";

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

function coverageLabel(s: string): string {
  const m: Record<string, string> = {
    gap: "Lücke",
    partial: "Teilweise",
    full: "Voll",
    planned_only: "Geplant",
  };
  return m[s] ?? s;
}

export interface CrossRegulationDashboardClientProps {
  tenantId: string;
  summary: CrossRegFrameworkSummaryDto[];
  requirements: RegulatoryRequirementRowDto[];
  controls: RegulatoryControlRowDto[];
}

export function CrossRegulationDashboardClient({
  tenantId,
  summary,
  requirements,
  controls,
}: CrossRegulationDashboardClientProps) {
  const [frameworkFilter, setFrameworkFilter] = useState<FrameworkFilter>("all");
  const [coverageFilter, setCoverageFilter] = useState<CoverageFilter>("all");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [criticalityFilter, setCriticalityFilter] = useState<string>("all");
  const [detail, setDetail] = useState<RequirementControlsDetailResponseDto | null>(null);
  const [detailErr, setDetailErr] = useState<string | null>(null);
  const [detailBusy, setDetailBusy] = useState(false);

  const filteredRequirements = useMemo(() => {
    return requirements.filter((r) => {
      if (frameworkFilter !== "all" && r.framework_key !== frameworkFilter) return false;
      if (coverageFilter !== "all" && r.coverage_status !== coverageFilter) return false;
      if (typeFilter !== "all" && r.requirement_type !== typeFilter) return false;
      if (criticalityFilter !== "all" && r.criticality !== criticalityFilter) return false;
      return true;
    });
  }, [requirements, frameworkFilter, coverageFilter, typeFilter, criticalityFilter]);

  const openDrilldown = async (requirementId: number) => {
    setDetailBusy(true);
    setDetailErr(null);
    try {
      const d = await fetchRequirementControlsDetail(tenantId, requirementId);
      setDetail(d);
    } catch (e) {
      setDetail(null);
      setDetailErr(e instanceof Error ? e.message : "Drilldown fehlgeschlagen");
    } finally {
      setDetailBusy(false);
    }
  };

  return (
    <div className="space-y-10">
      <section aria-label="Framework-Übersicht" data-testid="cross-reg-framework-cards">
        <p className={CH_SECTION_LABEL}>Framework-Übersicht</p>
        <p className="mt-1 max-w-3xl text-sm text-slate-600">
          Coverage aus tenant-spezifischen Controls und Verknüpfungen zu globalem
          Anforderungskatalog (Map once, comply many).
        </p>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {summary.map((f) => (
            <article key={f.framework_key} className={CH_CARD}>
              <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
                {f.framework_key}
              </p>
              <h3 className="mt-1 text-base font-bold text-slate-900">{f.name}</h3>
              {f.subtitle ? (
                <p className="text-xs font-medium text-slate-500">{f.subtitle}</p>
              ) : null}
              <div className="mt-3">
                <div className="flex justify-between text-xs text-slate-600">
                  <span>Coverage</span>
                  <span className="font-semibold tabular-nums text-slate-900">
                    {f.coverage_percent}%
                  </span>
                </div>
                <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-slate-200">
                  <div
                    className="h-full rounded-full bg-cyan-600 transition-[width]"
                    style={{ width: `${Math.min(100, f.coverage_percent)}%` }}
                  />
                </div>
              </div>
              <dl className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-600">
                <div>
                  <dt className="text-slate-500">Pflichten</dt>
                  <dd className="font-semibold text-slate-900">{f.total_requirements}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Lücken</dt>
                  <dd className="font-semibold text-amber-800">{f.gap_count}</dd>
                </div>
              </dl>
              <button
                type="button"
                className={`${CH_BTN_SECONDARY} mt-4 w-full justify-center text-xs`}
                onClick={() => setFrameworkFilter(f.framework_key)}
              >
                Details anzeigen
              </button>
            </article>
          ))}
        </div>
      </section>

      <section aria-label="Anforderungen und Controls" data-testid="cross-reg-requirements-table">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className={CH_SECTION_LABEL}>Anforderungen &amp; Controls</p>
            <p className="mt-1 text-sm text-slate-600">
              Filter und Drilldown zu verknüpften Controls, Systemen und Maßnahmen.
            </p>
          </div>
          <button
            type="button"
            className={`${CH_BTN_SECONDARY} text-xs`}
            onClick={() => {
              setFrameworkFilter("all");
              setCoverageFilter("all");
              setTypeFilter("all");
              setCriticalityFilter("all");
            }}
          >
            Filter zurücksetzen
          </button>
        </div>

        <div className="mt-4 flex flex-wrap gap-3">
          <label className="flex flex-col text-xs font-semibold text-slate-600">
            Framework
            <select
              className="mt-1 rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-sm"
              value={frameworkFilter}
              onChange={(e) => setFrameworkFilter(e.target.value as FrameworkFilter)}
              data-testid="filter-framework"
            >
              <option value="all">Alle</option>
              {summary.map((f) => (
                <option key={f.framework_key} value={f.framework_key}>
                  {f.name}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col text-xs font-semibold text-slate-600">
            Coverage
            <select
              className="mt-1 rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-sm"
              value={coverageFilter}
              onChange={(e) => setCoverageFilter(e.target.value as CoverageFilter)}
              data-testid="filter-coverage"
            >
              <option value="all">Alle</option>
              <option value="gap">Lücke</option>
              <option value="partial">Teilweise</option>
              <option value="full">Voll</option>
              <option value="planned_only">Geplant</option>
            </select>
          </label>
          <label className="flex flex-col text-xs font-semibold text-slate-600">
            Typ
            <select
              className="mt-1 rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-sm"
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              data-testid="filter-type"
            >
              <option value="all">Alle</option>
              <option value="governance">Governance</option>
              <option value="process">Prozess</option>
              <option value="technical">Technisch</option>
              <option value="documentation">Dokumentation</option>
            </select>
          </label>
          <label className="flex flex-col text-xs font-semibold text-slate-600">
            Kritikalität
            <select
              className="mt-1 rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-sm"
              value={criticalityFilter}
              onChange={(e) => setCriticalityFilter(e.target.value)}
              data-testid="filter-criticality"
            >
              <option value="all">Alle</option>
              <option value="high">Hoch</option>
              <option value="medium">Mittel</option>
              <option value="low">Niedrig</option>
            </select>
          </label>
        </div>

        <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200">
          <table className="min-w-[800px] w-full border-collapse text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2">Pflicht</th>
                <th className="px-3 py-2">Frameworks</th>
                <th className="px-3 py-2">Coverage</th>
                <th className="px-3 py-2">Controls</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              {filteredRequirements.map((r) => (
                <tr key={r.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-3 py-2 align-top">
                    <div className="font-semibold text-slate-900">
                      {r.code} – {r.title}
                    </div>
                    <div className="text-xs text-slate-500">{r.framework_name}</div>
                  </td>
                  <td className="px-3 py-2 align-top">
                    <div className="flex flex-wrap gap-1">
                      {r.related_framework_keys.map((k) => (
                        <span
                          key={k}
                          className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-700"
                        >
                          {badgeFramework(k)}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-3 py-2 align-top">
                    <span className="rounded-full bg-cyan-50 px-2 py-0.5 text-xs font-semibold text-cyan-900">
                      {coverageLabel(r.coverage_status)}
                    </span>
                  </td>
                  <td className="px-3 py-2 align-top text-xs text-slate-600">
                    <span className="font-semibold text-slate-800">{r.linked_control_count}</span> verknüpft
                    {r.primary_control_names.length > 0 ? (
                      <div className="mt-1 text-slate-500">
                        {r.primary_control_names.join(", ")}
                      </div>
                    ) : null}
                  </td>
                  <td className="px-3 py-2 align-top">
                    <button
                      type="button"
                      className={`${CH_BTN_PRIMARY} text-xs`}
                      onClick={() => void openDrilldown(r.id)}
                    >
                      Drilldown
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {detailBusy ? (
          <p className="mt-3 text-sm text-slate-500">Lade Drilldown…</p>
        ) : null}
        {detailErr ? (
          <p className="mt-3 text-sm text-rose-700">{detailErr}</p>
        ) : null}
        {detail ? (
          <div
            className={`${CH_CARD} mt-4 border-cyan-200 bg-cyan-50/30`}
            data-testid="cross-reg-drilldown"
          >
            <p className={CH_SECTION_LABEL}>Drilldown</p>
            <p className="mt-2 text-sm font-semibold text-slate-900">
              {detail.requirement.code} – {detail.requirement.title}
            </p>
            <ul className="mt-3 space-y-3 text-sm">
              {detail.links.map((l) => (
                <li key={l.link_id} className="rounded-lg border border-slate-200 bg-white p-3">
                  <div className="font-semibold text-slate-900">{l.control_name}</div>
                  <div className="mt-1 text-xs text-slate-600">
                    Deckung: {l.coverage_level} · Status: {l.control_status}
                    {l.owner_role ? ` · Rolle: ${l.owner_role}` : ""}
                  </div>
                  {l.ai_system_ids.length > 0 ? (
                    <div className="mt-2 text-xs">
                      <span className="font-semibold text-slate-700">KI-Systeme: </span>
                      {l.ai_system_ids.map((id) => (
                        <Link
                          key={id}
                          href={`/tenant/ai-systems/${id}`}
                          className="mr-2 text-cyan-800 underline"
                        >
                          {id}
                        </Link>
                      ))}
                    </div>
                  ) : null}
                  {l.policy_ids.length > 0 ? (
                    <div className="mt-1 text-xs text-slate-600">
                      Policy-IDs: {l.policy_ids.join(", ")} (
                      <Link href="/tenant/policies" className="text-cyan-800 underline">
                        Policies
                      </Link>
                      )
                    </div>
                  ) : null}
                  {l.action_ids.length > 0 ? (
                    <div className="mt-1 text-xs text-slate-600">
                      Action-IDs: {l.action_ids.join(", ")} (
                      <Link
                        href="/board/eu-ai-act-readiness#governance-actions"
                        className="text-cyan-800 underline"
                      >
                        Maßnahmen
                      </Link>
                      )
                    </div>
                  ) : null}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </section>

      <section aria-label="Controls zentriert" data-testid="cross-reg-controls-view">
        <p className={CH_SECTION_LABEL}>Map once, comply many</p>
        <p className="mt-1 max-w-3xl text-sm text-slate-600">
          Tenant-Controls mit Abdeckung mehrerer Framework-Pflichten. API unterstützt Verknüpfungen zu
          KI-Systemen, Policies und Governance-Actions.
        </p>
        {controls.length === 0 ? (
          <p className="mt-4 text-sm text-slate-600">
            Noch keine Controls angelegt. Legen Sie Controls an und verknüpfen Sie sie im Backend mit
            Pflichten (<code className="rounded bg-slate-100 px-1">compliance_requirement_control_links</code>
            ).
          </p>
        ) : (
          <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200">
            <table className="min-w-[720px] w-full border-collapse text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-3 py-2">Control</th>
                  <th className="px-3 py-2">Owner-Rolle</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Abdeckung</th>
                  <th className="px-3 py-2">Frameworks</th>
                </tr>
              </thead>
              <tbody>
                {controls.map((c) => (
                  <tr key={c.id} className="border-b border-slate-100 last:border-0">
                    <td className="px-3 py-2">
                      <div className="font-semibold text-slate-900">{c.name}</div>
                      <div className="text-xs text-slate-500">{c.control_type}</div>
                    </td>
                    <td className="px-3 py-2 text-xs text-slate-600">{c.owner_role ?? "–"}</td>
                    <td className="px-3 py-2 text-xs">{c.status}</td>
                    <td className="px-3 py-2 text-xs text-slate-700">
                      {c.requirement_count} Pflichten · {c.framework_count} Frameworks
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex flex-wrap gap-1">
                        {c.framework_keys.map((k) => (
                          <span
                            key={k}
                            className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-900"
                          >
                            {badgeFramework(k)}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
