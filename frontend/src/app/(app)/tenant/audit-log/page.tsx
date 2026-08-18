import Link from "next/link";
import React from "react";

import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import {
  TenantAuditLogTableClient,
  type AuditLogDemoRow,
} from "@/components/tenant/TenantAuditLogTableClient";
import {
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_PAGE_NAV_LINK,
  CH_SHELL,
} from "@/lib/boardLayout";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

function demoAuditRows(tenantId: string): AuditLogDemoRow[] {
  return [
  {
    id: "1",
    ts: "2025-03-18T09:15:00.000Z",
    actor: "isa@tenant.example",
    entityType: "AI-System",
    action: "UPDATE",
    tenant: tenantId,
    detail: "risk_level → high",
  },
  {
    id: "2",
    ts: "2025-03-19T14:22:00.000Z",
    actor: "system",
    entityType: "Evidence",
    action: "CREATE",
    tenant: tenantId,
    detail: "Upload DPIA (KI-Chatbot Vertrieb)",
  },
  {
    id: "3",
    ts: "2025-03-20T11:03:00.000Z",
    actor: "compliance@tenant.example",
    entityType: "Policy",
    action: "PUBLISH",
    tenant: tenantId,
    detail: "policy-eu-ai-act-v3",
  },
  {
    id: "4",
    ts: "2025-03-21T08:40:00.000Z",
    actor: "auditor@external.example",
    entityType: "Action",
    action: "READ",
    tenant: tenantId,
    detail: "Governance-Maßnahme #12",
  },
  {
    id: "5",
    ts: "2025-03-22T16:55:00.000Z",
    actor: "api-key:ingest",
    entityType: "AI-System",
    action: "IMPORT",
    tenant: tenantId,
    detail: "CSV Import 12 Zeilen",
  },
];
}

export default async function TenantAuditLogPage() {
  const tenantId = await getWorkspaceTenantIdServer();
  const demoRows = demoAuditRows(tenantId);
  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        eyebrow="Tenant"
        title="Audit & Evidence"
        description={
          <>
            Unveränderliche Audit-Spur für KI-Systeme, Policy-Entscheidungen und Mandanten-Aktionen –
            exportierbar für Prüfer und interne Revision. Evidence-Bundles bündeln Nachweise für NIS2,
            ISO 27001 und EU AI Act.
          </>
        }
        actions={
          <button type="button" className={`${CH_BTN_SECONDARY} text-sm`}>
            Export als CSV
          </button>
        }
        below={
          <>
            <Link href="/tenant/policies" className={CH_PAGE_NAV_LINK}>
              Policy Engine
            </Link>
            <Link href="/tenant/compliance-overview" className={CH_PAGE_NAV_LINK}>
              Compliance-Übersicht
            </Link>
          </>
        }
      />

      <TenantAuditLogTableClient tenantId={tenantId} rows={demoRows} />

      <section className={`${CH_CARD} overflow-hidden p-0`}>
        <div className="border-b border-slate-200/80 px-5 py-4">
          <h2 className="text-sm font-semibold text-slate-900">Evidence Bundles für Prüfungen</h2>
        </div>
        <div className="px-5 py-5 text-sm text-slate-600">
          <p>
            Hier können später prüfbare Evidence-Pakete (Screenshots, Logs, Policy-Snapshots,
            Klassifizierungsstände) für NIS2- und ISO-Audits bereitgestellt und versioniert werden.
          </p>
        </div>
      </section>
    </div>
  );
}
