import Link from "next/link";
import React from "react";

import {
  fetchTenantAISystems,
  fetchTenantSetupStatus,
  fetchTenantViolations,
  type TenantSetupStatus,
} from "@/lib/api";
import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import { GuidedSetupWizard } from "@/components/workspace/GuidedSetupWizard";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";
import {
  CH_BTN_PRIMARY,
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_SECTION_LABEL,
  CH_SHELL,
} from "@/lib/boardLayout";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.COMPLIANCEHUB_API_BASE_URL ||
  "http://localhost:8000";

type AISystem = {
  id: string;
  name: string;
  businessunit: string;
  risklevel: string;
  aiactcategory: string;
  status: string;
};

type Violation = {
  id: string;
  aisystemid: string;
  ruleid: string;
  message: string;
  createdat: string;
};

function classNames(...values: (string | false | null | undefined)[]) {
  return values.filter(Boolean).join(" ");
}

function defaultTenantSetupStatus(tenantId: string): TenantSetupStatus {
  return {
    tenant_id: tenantId,
    ai_inventory_completed: false,
    classification_completed: false,
    classification_coverage_ratio: 0,
    nis2_kpis_seeded: false,
    policies_published: false,
    actions_defined: false,
    evidence_attached: false,
    eu_ai_act_readiness_baseline_created: false,
    completed_steps: 0,
    total_steps: 7,
  };
}

export default async function TenantComplianceOverviewPage() {
  const activeTenant = await getWorkspaceTenantIdServer();

  let setupStatus: TenantSetupStatus = defaultTenantSetupStatus(activeTenant);
  let setupLoadFailed = false;
  try {
    setupStatus = await fetchTenantSetupStatus(activeTenant);
  } catch {
    setupLoadFailed = true;
  }

  const [systems, violations] = (await Promise.all([
    fetchTenantAISystems(activeTenant),
    fetchTenantViolations(activeTenant),
  ])) as [AISystem[], Violation[]];

  const totalSystems = systems.length;
  const highRisk = systems.filter((s) => s.risklevel === "high").length;
  const openViolations = violations.length;

  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        eyebrow="Tenant"
        title="Compliance-Übersicht"
        description="Konsolidierter Überblick über KI-Systeme, Risiken und Policy-Violations für diesen Mandanten – zentral für ISB und Betrieb."
        actions={
          <>
            <span className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-900">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" aria-hidden />
              Status OK
            </span>
            <button type="button" className={`${CH_BTN_SECONDARY} text-sm`}>
              Report exportieren
            </button>
            <Link href="/board/kpis" className={`${CH_BTN_PRIMARY} text-sm`}>
              Zum Board
            </Link>
          </>
        }
      />

      <GuidedSetupWizard initialStatus={setupStatus} loadFailed={setupLoadFailed} />

      <section
        aria-label="Workspace-Home"
        className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3"
      >
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>KI-Systeme</p>
          <p className="mt-2 text-sm text-slate-600">
            Register, Risiko und Verknüpfung zu Incidents, NIS2-KPIs und Nachweisen.
          </p>
          <Link href="/tenant/ai-systems" className={`${CH_BTN_PRIMARY} mt-4 inline-flex text-xs`}>
            Zum Register
          </Link>
        </article>
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>EU AI Act</p>
          <p className="mt-2 text-sm text-slate-600">
            Klassifikation, Anforderungen und operative Lückenschließung im Mandanten.
          </p>
          <Link href="/tenant/eu-ai-act" className={`${CH_BTN_SECONDARY} mt-4 inline-flex text-xs`}>
            Zum Cockpit
          </Link>
        </article>
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>NIS2 / KRITIS</p>
          <p className="mt-2 text-sm text-slate-600">
            Board-Drilldown zu Incident- und Supplier-Readiness für den Vorstand.
          </p>
          <Link href="/board/nis2-kritis" className={`${CH_BTN_SECONDARY} mt-4 inline-flex text-xs`}>
            Zum Board
          </Link>
        </article>
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Policies</p>
          <p className="mt-2 text-sm text-slate-600">
            Framework-Mappings und operative Policy-Engine für den Workspace.
          </p>
          <Link href="/tenant/policies" className={`${CH_BTN_SECONDARY} mt-4 inline-flex text-xs`}>
            Policies öffnen
          </Link>
        </article>
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Blueprints</p>
          <p className="mt-2 text-sm text-slate-600">
            Vorlagen und Playbooks für EU AI Act, NIS2 und ISO 42001.
          </p>
          <Link href="/tenant/blueprints" className={`${CH_BTN_SECONDARY} mt-4 inline-flex text-xs`}>
            Blueprints
          </Link>
        </article>
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Audit-Log</p>
          <p className="mt-2 text-sm text-slate-600">
            Unveränderliche Ereignisspur für Revision und Regulatorik.
          </p>
          <Link href="/tenant/audit-log" className={`${CH_BTN_SECONDARY} mt-4 inline-flex text-xs`}>
            Audit-Log
          </Link>
        </article>
      </section>

      <section
        aria-label="Mandant und technische Anbindung"
        className="grid gap-4 lg:grid-cols-3"
      >
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Mandant</p>
          <p className="mt-2 font-mono text-sm font-semibold text-slate-900">{activeTenant}</p>
          <p className="mt-2 text-xs leading-relaxed text-slate-600">
            Anzeigename und Stammdaten des Mandanten; produktiv über Admin-API
            gepflegt.
          </p>
          <Link href="/tenant/ai-systems" className={`${CH_BTN_SECONDARY} mt-4 text-xs`}>
            Zum AI-Register
          </Link>
        </article>
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>API &amp; Zugriff</p>
          <dl className="mt-3 space-y-2 text-xs text-slate-600">
            <div>
              <dt className="font-semibold text-slate-500">Basis-URL</dt>
              <dd className="mt-0.5 break-all font-mono text-slate-800">{API_BASE_URL}</dd>
            </div>
            <div>
              <dt className="font-semibold text-slate-500">API-Key</dt>
              <dd className="mt-0.5 text-slate-800">
                Konfiguriert als{" "}
                <code className="rounded bg-slate-100 px-1">NEXT_PUBLIC_API_KEY</code> /{" "}
                <code className="rounded bg-slate-100 px-1">COMPLIANCEHUB_API_KEY</code>
                . Werte werden hier nicht angezeigt; Geheimnisse besser nur serverseitig
                (<code className="rounded bg-slate-100 px-1">COMPLIANCEHUB_*</code>) setzen.
              </dd>
            </div>
          </dl>
        </article>
        <article className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Framework-Scoping</p>
          <p className="mt-2 text-sm text-slate-600">
            Aktiver GRC-Stack: EU AI Act (High-Risk), NIS2 / KRITIS-Bezug, ISO 42001
            AI-Managementsystem, DSGVO-DPIA für High-Risk.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link href="/board/kpis" className={`${CH_BTN_SECONDARY} text-xs`}>
              Board KPIs
            </Link>
            <Link href="/board/eu-ai-act-readiness" className={`${CH_BTN_SECONDARY} text-xs`}>
              EU AI Act
            </Link>
          </div>
        </article>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <div className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>KI-Systeme gesamt</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-slate-900">{totalSystems}</p>
          <p className="mt-2 text-xs text-slate-600">
            Registrierte produktive und in Prüfung befindliche Systeme.
          </p>
        </div>
        <div className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>High-Risk</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-amber-700">{highRisk}</p>
          <p className="mt-2 text-xs text-slate-600">
            Nach AI-Act-Kategorie und Risikoeinstufung.
          </p>
        </div>
        <div className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Offene Violations</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-rose-700">{openViolations}</p>
          <p className="mt-2 text-xs text-slate-600">Aggregiert über alle Systeme.</p>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-3">
        <section className={`${CH_CARD} lg:col-span-2 overflow-hidden p-0`}>
          <div className="flex items-center justify-between border-b border-[var(--sbs-border)] px-5 py-3">
            <h2 className="text-sm font-bold text-[var(--sbs-text-primary)]">
              AI‑Systeme
            </h2>
            <span className="text-xs text-[var(--sbs-text-secondary)]">
              {totalSystems} Einträge
            </span>
          </div>
          <div className="sbs-table-wrap">
            <table className="sbs-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Business Unit</th>
                  <th>Risk Level</th>
                  <th>AI Act</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {systems.map((s) => (
                  <tr key={s.id}>
                    <td>
                      <div className="font-semibold text-[var(--sbs-text-primary)]">
                        {s.name}
                      </div>
                      <div className="text-xs text-[var(--sbs-text-muted)]">
                        {s.id}
                      </div>
                    </td>
                    <td className="text-[var(--sbs-text-secondary)]">
                      {s.businessunit}
                    </td>
                    <td>
                      <span
                        className={classNames(
                          "inline-flex rounded-full px-2 py-0.5 text-xs font-semibold",
                          s.risklevel === "high" &&
                            "border border-rose-200 bg-rose-50 text-rose-800",
                          s.risklevel === "limited" &&
                            "border border-amber-200 bg-amber-50 text-amber-900",
                          s.risklevel === "low" &&
                            "border border-emerald-200 bg-emerald-50 text-emerald-900",
                        )}
                      >
                        {s.risklevel}
                      </span>
                    </td>
                    <td className="text-xs text-[var(--sbs-text-secondary)]">
                      {s.aiactcategory}
                    </td>
                    <td className="text-xs">
                      <span className="inline-flex rounded-full border border-[var(--sbs-border)] bg-slate-50 px-2 py-0.5 text-[var(--sbs-text-secondary)]">
                        {s.status}
                      </span>
                    </td>
                  </tr>
                ))}
                {systems.length === 0 && (
                  <tr>
                    <td
                      colSpan={5}
                      className="py-8 text-center text-sm text-[var(--sbs-text-secondary)]"
                    >
                      Noch keine AI‑Systeme für diesen Tenant erfasst.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className={`${CH_CARD} overflow-hidden p-0`}>
          <div className="flex items-center justify-between border-b border-[var(--sbs-border)] px-5 py-3">
            <h2 className="text-sm font-bold text-[var(--sbs-text-primary)]">
              Aktuelle Violations
            </h2>
            <span className="text-xs text-[var(--sbs-text-secondary)]">
              {openViolations} offen
            </span>
          </div>
          <div className="max-h-80 space-y-3 overflow-y-auto px-5 py-4 text-xs">
            {violations.map((v) => (
              <div
                key={v.id}
                className="rounded-lg border border-rose-200 bg-rose-50/80 p-3 text-rose-950"
              >
                <div className="mb-1 font-medium">{v.message}</div>
                <div className="flex justify-between text-[11px] text-rose-800/90">
                  <span>System: {v.aisystemid}</span>
                  <span>Rule: {v.ruleid}</span>
                </div>
                <div className="mt-1 text-[11px] text-rose-700/80">
                  {new Date(v.createdat).toLocaleString("de-DE")}
                </div>
              </div>
            ))}
            {violations.length === 0 && (
              <div className="text-center text-[var(--sbs-text-secondary)]">
                Aktuell keine offenen Violations.
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
