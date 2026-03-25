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

const TENANT_ID =
  process.env.NEXT_PUBLIC_TENANT_ID ||
  process.env.COMPLIANCEHUB_TENANT_ID ||
  "tenant-overview-001";

const DEMO_AUDIT_ROWS: AuditLogDemoRow[] = [
  {
    id: "1",
    ts: "2025-03-18T09:15:00.000Z",
    actor: "isa@tenant.example",
    entityType: "AI-System",
    action: "UPDATE",
    tenant: TENANT_ID,
    detail: "risk_level → high",
  },
  {
    id: "2",
    ts: "2025-03-19T14:22:00.000Z",
    actor: "system",
    entityType: "Evidence",
    action: "CREATE",
    tenant: TENANT_ID,
    detail: "Upload DPIA (KI-Chatbot Vertrieb)",
  },
  {
    id: "3",
    ts: "2025-03-20T11:03:00.000Z",
    actor: "compliance@tenant.example",
    entityType: "Policy",
    action: "PUBLISH",
    tenant: TENANT_ID,
    detail: "policy-eu-ai-act-v3",
  },
  {
    id: "4",
    ts: "2025-03-21T08:40:00.000Z",
    actor: "auditor@external.example",
    entityType: "Action",
    action: "READ",
    tenant: TENANT_ID,
    detail: "Governance-Maßnahme #12",
  },
  {
    id: "5",
    ts: "2025-03-22T16:55:00.000Z",
    actor: "api-key:ingest",
    entityType: "AI-System",
    action: "IMPORT",
    tenant: TENANT_ID,
    detail: "CSV Import 12 Zeilen",
  },
];

export default async function TenantAuditLogPage() {
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

      <TenantAuditLogTableClient tenantId={TENANT_ID} rows={DEMO_AUDIT_ROWS} />

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
