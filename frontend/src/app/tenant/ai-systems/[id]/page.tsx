import Link from "next/link";
import React from "react";

import { EvidenceAttachmentsSection } from "@/components/evidence/EvidenceAttachmentsSection";
import { GovernanceViewFeatureTelemetry } from "@/components/workspace/GovernanceViewFeatureTelemetry";
import { AiActDocumentationClient } from "@/components/tenant/AiActDocumentationClient";
import { AiSystemKpiPanel } from "@/components/tenant/AiSystemKpiPanel";
import { AiSystemSectionNav } from "@/components/tenant/AiSystemSectionNav";
import { Nis2KpiAiAssistClient } from "@/components/tenant/Nis2KpiAiAssistClient";
import {
  fetchAiSystemRegulatoryContext,
  fetchEuAiActReadiness,
  fetchIncidentsBySystem,
  fetchNis2KritisKpis,
  fetchSystemCompliance,
  fetchTenantAISystems,
  fetchAISystemViolations,
  fetchClassification,
  type AISystem,
} from "@/lib/api";
import { featureAiKpiKri, featureCrossRegulationDashboard } from "@/lib/config";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";
import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import {
  CH_BTN_PRIMARY,
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_PAGE_NAV_LINK,
  CH_SHELL,
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
  const workspaceTenantId = await getWorkspaceTenantIdServer();
  const systems = await fetchTenantAISystems(workspaceTenantId);
  const system = systems.find((x) => x.id === id);

  if (!system) {
    return (
      <div className={CH_SHELL}>
        <EnterprisePageHeader
          eyebrow="Tenant"
          title="KI-System"
          description="Dieses System ist im Register nicht vorhanden oder der Zugriff wurde verweigert."
        />
        <Link href="/tenant/ai-systems" className={CH_BTN_SECONDARY}>
          Zurück zum Register
        </Link>
      </div>
    );
  }

  const [violations, nis2, compliance, bySystem, readiness] = await Promise.all([
    fetchAISystemViolations(workspaceTenantId, id).catch(() => []),
    fetchNis2KritisKpis(workspaceTenantId, id).catch(() => ({
      kpis: [],
      recommended: null,
    })),
    fetchSystemCompliance(workspaceTenantId, id).catch(() => []),
    fetchIncidentsBySystem(workspaceTenantId).catch(() => []),
    fetchEuAiActReadiness(workspaceTenantId).catch(() => null),
  ]);

  const regulatoryHints =
    featureCrossRegulationDashboard() && system
      ? await fetchAiSystemRegulatoryContext(workspaceTenantId, id).catch(() => [])
      : [];

  let classification: Awaited<ReturnType<typeof fetchClassification>> | null = null;
  try {
    classification = await fetchClassification(workspaceTenantId, id);
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
    <div className={CH_SHELL}>
      <GovernanceViewFeatureTelemetry
        tenantId={workspaceTenantId}
        featureName="ai_system_detail"
        routeName={`/tenant/ai-systems/${id}`}
        aiSystemId={id}
      />
      <EnterprisePageHeader
        eyebrow="Tenant · KI-System"
        title={system.name}
        description={`${pickBu(system)} · technische ID ${system.id}`}
        actions={
          <>
            <Link href="/tenant/ai-systems" className={CH_BTN_SECONDARY}>
              Register
            </Link>
            <Link href="/tenant/eu-ai-act" className={CH_BTN_PRIMARY}>
              EU AI Act
            </Link>
          </>
        }
        below={
          <>
            <Link href="/board/incidents" className={CH_PAGE_NAV_LINK}>
              Board: Incidents
            </Link>
            <Link href="/board/nis2-kritis" className={CH_PAGE_NAV_LINK}>
              NIS2-Drilldown
            </Link>
          </>
        }
      />

      <AiSystemSectionNav />

      <section
        id="sec-stammdaten"
        className={`${CH_CARD} scroll-mt-32`}
        aria-label="Stammdaten"
      >
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

      <section
        id="sec-evidenz"
        className={`${CH_CARD} scroll-mt-32`}
        aria-label="Evidenz und Dokumente"
      >
        <h2 className="text-base font-semibold text-slate-900">
          Evidenz & Dokumente
        </h2>
        <div className="mt-4">
          <EvidenceAttachmentsSection
            title="Nachweise zu diesem KI-System"
            description="Upload von DPIA, Runbooks, Policies, Verträgen und weiteren Prüfungsnachweisen (EU AI Act, NIS2, ISO 42001). Dateien sind mandantenisoliert; technische Ablage erfolgt ohne sensible Namen im Speicherpfad."
            aiSystemId={id}
          />
        </div>
      </section>

      <section
        id="sec-klassifikation"
        className={`${CH_CARD} scroll-mt-32`}
        aria-label="Klassifikation EU AI Act"
      >
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

      {featureAiKpiKri() ? (
        <section
          id="sec-ai-kpis"
          className={`${CH_CARD} scroll-mt-32`}
          aria-label="AI KPIs und KRIs"
        >
          <h2 className="text-base font-semibold text-slate-900">AI KPIs &amp; KRIs</h2>
          <p className="mt-1 text-sm text-slate-600">
            Systembezogene Messgrößen für Post-Market-Monitoring (EU AI Act) und Performance
            Evaluation (ISO 42001). Werte pro Periode erfassen; Trends und Ampeln werden aus den
            letzten Perioden abgeleitet.
          </p>
          <div className="mt-4">
            <AiSystemKpiPanel tenantId={workspaceTenantId} systemId={id} />
          </div>
        </section>
      ) : null}

      <section
        id="sec-nis2"
        className={`${CH_CARD} scroll-mt-32`}
        aria-label="NIS2 und KRITIS KPIs"
      >
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
        <Nis2KpiAiAssistClient aiSystemId={id} />
      </section>

      <section id="sec-incidents" className={`${CH_CARD} scroll-mt-32`} aria-label="Incidents">
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

      {regulatoryHints.length > 0 ? (
        <section
          className={`${CH_CARD} scroll-mt-32`}
          aria-label="Cross-Regulation-Kontext"
        >
          <h2 className="text-base font-semibold text-slate-900">
            Cross-Regulation (über verknüpfte Controls)
          </h2>
          <p className="mt-1 text-xs text-slate-500">
            Pflichten aus dem Regelwerkskatalog, die über Controls mit diesem KI-System verknüpft sind.
          </p>
          <ul className="mt-3 space-y-2 text-sm">
            {regulatoryHints.map((h) => (
              <li
                key={`${h.requirement_id}-${h.framework_key}`}
                className="rounded-lg border border-cyan-100 bg-cyan-50/50 px-3 py-2"
              >
                <span className="font-semibold text-slate-900">
                  {h.framework_key.toUpperCase()} {h.code}
                </span>
                <span className="text-slate-700"> – {h.title}</span>
                <div className="mt-1 text-xs text-slate-500">via {h.via_control_name}</div>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs">
            <Link
              href="/tenant/cross-regulation-dashboard"
              className="font-semibold text-cyan-800 underline"
            >
              Zum Cross-Regulation Dashboard
            </Link>
          </p>
        </section>
      ) : featureCrossRegulationDashboard() ? (
        <section className={`${CH_CARD} scroll-mt-32`} aria-label="Cross-Regulation-Hinweis">
          <h2 className="text-base font-semibold text-slate-900">Cross-Regulation</h2>
          <p className="mt-2 text-sm text-slate-600">
            Noch keine Pflichten über Controls mit diesem System verknüpft. Im Dashboard können Sie
            Coverage über alle Frameworks steuern; Verknüpfungen erfolgen über tenant-Controls und Links
            im Backend-Datenmodell.
          </p>
          <Link href="/tenant/cross-regulation-dashboard" className={`${CH_BTN_SECONDARY} mt-3 inline-flex text-xs`}>
            Cross-Regulation Dashboard
          </Link>
        </section>
      ) : null}

      <section
        id="sec-compliance"
        className={`${CH_CARD} scroll-mt-32`}
        aria-label="Compliance-Status"
      >
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

      <section
        id="sec-violations"
        className={`${CH_CARD} scroll-mt-32`}
        aria-label="Policy Violations"
      >
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

      {pickRisk(system) === "high" ? (
        <div className="scroll-mt-32">
          <AiActDocumentationClient aiSystemId={id} />
        </div>
      ) : null}

      <section
        id="sec-massnahmen"
        className={`${CH_CARD} scroll-mt-32`}
        aria-label="Governance-Maßnahmen"
      >
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
