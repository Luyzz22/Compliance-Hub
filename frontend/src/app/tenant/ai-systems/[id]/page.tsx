import Link from "next/link";
import React from "react";

import {
  fetchEuAiActReadiness,
  fetchIncidentsBySystem,
  fetchNis2KritisKpis,
  fetchSystemCompliance,
  fetchTenantAISystems,
  fetchAISystemViolations,
  fetchClassification,
  type AISystem,
} from "@/lib/api";
import {
  CH_BTN_PRIMARY,
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_PAGE_SUB,
  CH_PAGE_TITLE,
  CH_SECTION_LABEL,
} from "@/lib/boardLayout";

const KPI_LABEL: Record<string, string> = {
  INCIDENT_RESPONSE_MATURITY: "Incident-Readiness",
  SUPPLIER_RISK_COVERAGE: "Supplier-Risk",
  OT_IT_SEGREGATION: "OT/IT-Segregation",
};

type PageProps = { params: Promise<{ id: string }> };

function pickBu(s: AISystem): string {
  return s.business_unit ?? s.businessunit ?? "–";
}

function pickRisk(s: AISystem): string {
  return s.risk_level ?? s.risklevel ?? "–";
}

export default async function TenantAiSystemDetailPage({ params }: PageProps) {
  const { id } = await params;
  const systems = await fetchTenantAISystems();
  const system = systems.find((x) => x.id === id);

  if (!system) {
    return (
      <div className="min-w-0">
        <header className="mb-8">
          <h1 className={CH_PAGE_TITLE}>KI-System</h1>
          <p className={CH_PAGE_SUB}>Das System wurde nicht gefunden.</p>
        </header>
        <Link href="/tenant/ai-systems" className={CH_BTN_SECONDARY}>
          Zurück zum Register
        </Link>
      </div>
    );
  }

  const [violations, nis2, compliance, bySystem, readiness] = await Promise.all([
    fetchAISystemViolations(id).catch(() => []),
    fetchNis2KritisKpis(id).catch(() => ({ kpis: [], recommended: null })),
    fetchSystemCompliance(id).catch(() => []),
    fetchIncidentsBySystem().catch(() => []),
    fetchEuAiActReadiness().catch(() => null),
  ]);

  let classification: Awaited<ReturnType<typeof fetchClassification>> | null = null;
  try {
    classification = await fetchClassification(id);
  } catch {
    classification = null;
  }

  const incidentRow = bySystem.find((r) => r.ai_system_id === id);
  const actionsForSystem =
    readiness?.open_governance_actions.filter((a) => a.related_ai_system_id === id) ??
    [];

  const complianceDone = compliance.filter((c) => c.status === "completed").length;
  const complianceOpen = compliance.filter((c) => c.status === "not_started").length;

  return (
    <div className="min-w-0 space-y-8">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className={CH_SECTION_LABEL}>KI-System</p>
          <h1 className={`${CH_PAGE_TITLE} mt-1`}>{system.name}</h1>
          <p className={CH_PAGE_SUB}>{pickBu(system)} · ID {system.id}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/tenant/ai-systems" className={CH_BTN_SECONDARY}>
            Register
          </Link>
          <Link href="/tenant/eu-ai-act" className={CH_BTN_PRIMARY}>
            EU AI Act Cockpit
          </Link>
        </div>
      </header>

      <section className={CH_CARD} aria-label="Stammdaten">
        <h2 className="text-base font-semibold text-slate-900">Stammdaten</h2>
        <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-xs font-medium text-slate-500">Business Unit</dt>
            <dd className="mt-0.5 font-medium text-slate-900">{pickBu(system)}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-slate-500">Status</dt>
            <dd className="mt-0.5 font-medium text-slate-900">{system.status ?? "–"}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-slate-500">Risk Level</dt>
            <dd className="mt-0.5 font-medium text-slate-900">{pickRisk(system)}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-slate-500">AI Act Kategorie</dt>
            <dd className="mt-0.5 font-medium text-slate-900">
              {system.ai_act_category ?? system.aiactcategory ?? "–"}
            </dd>
          </div>
          {system.owner_email || system.owneremail ? (
            <div className="sm:col-span-2">
              <dt className="text-xs font-medium text-slate-500">Owner</dt>
              <dd className="mt-0.5 font-medium text-slate-900">
                {system.owner_email ?? system.owneremail}
              </dd>
            </div>
          ) : null}
        </dl>
      </section>

      <section className={CH_CARD} aria-label="Klassifikation EU AI Act">
        <h2 className="text-base font-semibold text-slate-900">Klassifikation</h2>
        {classification ? (
          <dl className="mt-4 space-y-2 text-sm text-slate-700">
            <div className="flex flex-wrap justify-between gap-2">
              <dt className="text-slate-500">Risiko-Stufe</dt>
              <dd className="font-semibold text-slate-900">{classification.risk_level}</dd>
            </div>
            <div className="flex flex-wrap justify-between gap-2">
              <dt className="text-slate-500">Pfad</dt>
              <dd className="font-medium">{classification.classification_path}</dd>
            </div>
            <p className="mt-3 rounded-xl bg-slate-50 p-3 text-xs leading-relaxed text-slate-600">
              {classification.classification_rationale}
            </p>
          </dl>
        ) : (
          <p className="mt-3 text-sm text-slate-500">
            Noch keine Klassifikation hinterlegt oder API nicht verfügbar.
          </p>
        )}
      </section>

      <section className={CH_CARD} aria-label="NIS2 und KRITIS KPIs">
        <h2 className="text-base font-semibold text-slate-900">NIS2 / KRITIS KPIs</h2>
        {nis2.kpis.length === 0 ? (
          <p className="mt-3 text-sm text-slate-500">Keine KPI-Zeilen für dieses System.</p>
        ) : (
          <ul className="mt-4 divide-y divide-slate-100">
            {nis2.kpis.map((k) => (
              <li
                key={k.id}
                className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0"
              >
                <span className="text-sm font-medium text-slate-800">
                  {KPI_LABEL[k.kpi_type] ?? k.kpi_type}
                </span>
                <span className="tabular-nums text-lg font-semibold text-slate-900">
                  {k.value_percent}%
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className={CH_CARD} aria-label="Incidents">
        <h2 className="text-base font-semibold text-slate-900">Incidents (Aggregat)</h2>
        {incidentRow ? (
          <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-xs font-medium text-slate-500">Anzahl (12 Mon.)</dt>
              <dd className="mt-0.5 text-2xl font-semibold tabular-nums text-slate-900">
                {incidentRow.incident_count}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-slate-500">Letztes Incident</dt>
              <dd className="mt-0.5 font-medium text-slate-800">
                {incidentRow.last_incident_at
                  ? new Date(incidentRow.last_incident_at).toLocaleString("de-DE")
                  : "–"}
              </dd>
            </div>
          </dl>
        ) : (
          <p className="mt-3 text-sm text-slate-500">Keine Incident-Aggregation für dieses System.</p>
        )}
        <p className="mt-4">
          <Link
            href="/board/incidents"
            className="text-sm font-semibold text-cyan-700 underline decoration-cyan-700/30 hover:text-cyan-900"
          >
            Zur Incident-Übersicht
          </Link>
        </p>
      </section>

      <section className={CH_CARD} aria-label="Compliance-Status">
        <h2 className="text-base font-semibold text-slate-900">EU AI Act Compliance (Überblick)</h2>
        <p className="mt-1 text-xs text-slate-500">
          {compliance.length} Anforderungen geladen · {complianceDone} erfüllt ·{" "}
          {complianceOpen} offen
        </p>
        {compliance.length > 0 ? (
          <ul className="mt-4 max-h-56 space-y-2 overflow-y-auto text-sm">
            {compliance.slice(0, 12).map((c) => (
              <li
                key={c.requirement_id}
                className="flex items-center justify-between gap-2 rounded-lg border border-slate-100 bg-slate-50/80 px-3 py-2"
              >
                <span className="min-w-0 truncate font-medium text-slate-800">
                  {c.requirement_id}
                </span>
                <span className="shrink-0 rounded-full bg-white px-2 py-0.5 text-xs font-semibold text-slate-600 ring-1 ring-slate-200">
                  {c.status}
                </span>
              </li>
            ))}
          </ul>
        ) : null}
      </section>

      <section className={CH_CARD} aria-label="Policy Violations">
        <h2 className="text-base font-semibold text-slate-900">Violations</h2>
        {violations.length === 0 ? (
          <p className="mt-3 text-sm text-slate-500">Keine offenen Violations für dieses System.</p>
        ) : (
          <ul className="mt-4 space-y-3">
            {violations.map((v) => (
              <li
                key={v.id}
                className="rounded-xl border border-rose-100 bg-rose-50/60 px-4 py-3 text-sm text-rose-950"
              >
                <p className="font-medium">{v.message}</p>
                <p className="mt-1 text-xs text-rose-800/80">
                  {new Date(v.createdat).toLocaleString("de-DE")}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className={CH_CARD} aria-label="Governance-Maßnahmen">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-base font-semibold text-slate-900">Offene Maßnahmen</h2>
          <Link href="/board/eu-ai-act-readiness#governance-actions" className={CH_BTN_SECONDARY}>
            Alle Maßnahmen
          </Link>
        </div>
        {actionsForSystem.length === 0 ? (
          <p className="mt-3 text-sm text-slate-500">
            Keine offenen Maßnahmen mit direkter System-Verknüpfung.
          </p>
        ) : (
          <ul className="mt-4 divide-y divide-slate-100">
            {actionsForSystem.map((a) => (
              <li key={a.id} className="py-3 first:pt-0">
                <p className="font-semibold text-slate-900">{a.title}</p>
                <p className="mt-1 text-xs text-slate-500">
                  {a.related_requirement} · {a.status}
                  {a.due_date
                    ? ` · fällig ${new Date(a.due_date).toLocaleDateString("de-DE")}`
                    : ""}
                  {a.owner ? ` · ${a.owner}` : ""}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
