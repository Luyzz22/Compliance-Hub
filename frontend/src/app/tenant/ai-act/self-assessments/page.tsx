import Link from "next/link";

import { StartNewSelfAssessmentButton } from "@/components/ai-act/StartNewSelfAssessmentButton";
import { StatusBadge } from "@/components/governance/StatusBadge";
import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import { listSelfAssessments } from "@/lib/aiActSelfAssessmentApi";
import { tenantAiActSelfAssessmentDetailPath } from "@/lib/aiActSelfAssessmentRoutes";
import {
  CH_CARD,
  CH_PAGE_NAV_LINK,
  CH_SECTION_LABEL,
  CH_SHELL,
} from "@/lib/boardLayout";
import { formatGovernanceDateTime } from "@/lib/formatGovernanceDate";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

export default async function TenantSelfAssessmentsListPage() {
  const tenantId = await getWorkspaceTenantIdServer();
  const res = await listSelfAssessments(tenantId);

  const rows = res.ok ? res.data : [];
  const loadError = !res.ok ? `${res.status}: ${res.message}` : null;

  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        eyebrow="Enterprise · EU AI Act"
        title="Self-Assessment Workspace"
        description={
          <>
            Mandantenbezogene Runs für die EU-AI-Act-Selbsteinschätzung — Status, gebundenes
            KI-System und Schema-Version auf einen Blick. Daten kommen aus dem ComplianceHub-API.
          </>
        }
        breadcrumbs={[
          { label: "Tenant", href: "/tenant/compliance-overview" },
          { label: "Self-Assessments" },
        ]}
        actions={
          <div className="flex flex-col items-stretch gap-2 sm:flex-row sm:items-center">
            <StartNewSelfAssessmentButton tenantId={tenantId} />
            <Link href="/tenant/eu-ai-act" className={`${CH_PAGE_NAV_LINK} text-center sm:text-left`}>
              Zur EU-AI-Act-Übersicht
            </Link>
          </div>
        }
      />

      {loadError ? (
        <div
          className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900 shadow-sm"
          role="alert"
        >
          <p className="font-semibold">Liste konnte nicht geladen werden</p>
          <p className="mt-1 text-rose-800">{loadError}</p>
        </div>
      ) : null}

      <section className={CH_CARD}>
        <p className={CH_SECTION_LABEL}>Alle Runs</p>
        <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200/80">
          <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
            <thead className="bg-slate-50/90 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">KI-System</th>
                <th className="px-4 py-3">Schema</th>
                <th className="px-4 py-3">Gestartet</th>
                <th className="px-4 py-3">Abgeschlossen</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {rows.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-slate-500">
                    Keine Self-Assessments vorhanden. Starten Sie einen neuen Run über die Aktion
                    oben.
                  </td>
                </tr>
              ) : (
                rows.map((row) => {
                  const nameOrId = row.ai_system_name ?? row.ai_system_id ?? "—";
                  return (
                    <tr key={row.session_id} className="transition hover:bg-slate-50/90">
                      <td className="px-4 py-3">
                        <StatusBadge status={String(row.status)} />
                      </td>
                      <td className="px-4 py-3 text-slate-700">{nameOrId}</td>
                      <td className="px-4 py-3 text-slate-600">{row.schema_version ?? "—"}</td>
                      <td className="px-4 py-3 text-slate-600">
                        {formatGovernanceDateTime(row.started_at)}
                      </td>
                      <td className="px-4 py-3 text-slate-600">
                        {formatGovernanceDateTime(row.completed_at)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Link
                          href={tenantAiActSelfAssessmentDetailPath(row.session_id)}
                          className={CH_PAGE_NAV_LINK}
                        >
                          Öffnen
                        </Link>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
