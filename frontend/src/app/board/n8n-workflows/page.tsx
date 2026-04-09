"use client";

import React, { useState } from "react";
import Link from "next/link";

import {
  CH_BTN_PRIMARY,
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_PAGE_NAV_LINK,
  CH_SECTION_LABEL,
} from "@/lib/boardLayout";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.COMPLIANCEHUB_API_BASE_URL ||
  "http://localhost:8000";
const API_KEY =
  process.env.NEXT_PUBLIC_API_KEY ||
  process.env.COMPLIANCEHUB_API_KEY ||
  "tenant-overview-key";
const TENANT_ID =
  process.env.NEXT_PUBLIC_TENANT_ID ||
  process.env.COMPLIANCEHUB_TENANT_ID ||
  "tenant-overview-001";

interface WorkflowDef {
  id: string;
  name: string;
  description: string;
  schedule: string;
  type: string;
}

const WORKFLOWS: WorkflowDef[] = [
  {
    id: "monthly_board_report",
    name: "Monatlicher Board PDF-Report",
    description:
      "Automatische Generierung und E-Mail-Zustellung des PDF/A-3 Board-Reports am 1. jedes Monats.",
    schedule: "Monatlich (1. des Monats, 06:00 UTC)",
    type: "monthly_board_report",
  },
  {
    id: "datev_monthly_export",
    name: "DATEV Monatsexport",
    description:
      "Monatlicher DATEV EXTF-Export mit automatischer E-Mail-Zustellung an die Finanzbuchhaltung.",
    schedule: "Monatlich (1. des Monats, 07:00 UTC)",
    type: "datev_monthly_export",
  },
  {
    id: "deadline_reminder",
    name: "Deadline-Reminder",
    description:
      "Wöchentliche Prüfung auf bevorstehende regulatorische Fristen (30/14/7 Tage) mit E-Mail-Benachrichtigung.",
    schedule: "Wöchentlich (Montag, 08:00 UTC)",
    type: "deadline_reminder",
  },
  {
    id: "gap_analysis_trigger",
    name: "Gap-Analyse-Trigger",
    description:
      "Webhook-gesteuerter Trigger für Gap-Analysen bei Norm-Updates oder neuen Incidents.",
    schedule: "Webhook (on-demand)",
    type: "gap_analysis_trigger",
  },
  {
    id: "access_review_reminder",
    name: "Access-Review-Reminder",
    description:
      "Quartalsweiser Reminder für die Überprüfung privilegierter Rollen und Zugriffsrechte.",
    schedule: "Quartalsweise (1. des Quartals, 09:00 UTC)",
    type: "access_review_reminder",
  },
];

export default function N8nWorkflowsPage() {
  const [triggerResult, setTriggerResult] = useState<Record<string, string>>(
    {},
  );
  const [loading, setLoading] = useState<string | null>(null);

  async function handleTrigger(workflowType: string) {
    setLoading(workflowType);
    setTriggerResult((prev) => ({ ...prev, [workflowType]: "" }));

    try {
      const opaRole = process.env.NEXT_PUBLIC_OPA_USER_ROLE?.trim();
      const headers: Record<string, string> = {
        "x-api-key": API_KEY,
        "x-tenant-id": TENANT_ID,
        "Content-Type": "application/json",
      };
      if (opaRole) headers["x-opa-user-role"] = opaRole;

      const res = await fetch(
        `${API_BASE_URL}/api/v1/enterprise/n8n/webhook`,
        {
          method: "POST",
          headers,
          body: JSON.stringify({
            event_type: workflowType,
            data: { triggered_by: "admin_ui", timestamp: new Date().toISOString() },
          }),
        },
      );

      if (res.status === 403) {
        setTriggerResult((prev) => ({
          ...prev,
          [workflowType]:
            "❌ Zugriff verweigert — erfordert TENANT_ADMIN oder COMPLIANCE_ADMIN.",
        }));
        return;
      }
      if (!res.ok) {
        setTriggerResult((prev) => ({
          ...prev,
          [workflowType]: `❌ Fehler (HTTP ${res.status})`,
        }));
        return;
      }

      const body = await res.json();
      setTriggerResult((prev) => ({
        ...prev,
        [workflowType]: `✅ Akzeptiert (Correlation: ${body.correlation_id})`,
      }));
    } catch (e) {
      setTriggerResult((prev) => ({
        ...prev,
        [workflowType]:
          e instanceof Error ? `❌ ${e.message}` : "❌ Fehler",
      }));
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="min-w-0">
      <div className="mb-6 flex flex-wrap items-center gap-4">
        <h1 className="text-2xl font-semibold text-slate-900">
          n8n Workflow Automation
        </h1>
        <Link href="/board/executive-dashboard" className={CH_PAGE_NAV_LINK}>
          Executive Dashboard
        </Link>
        <Link href="/board/datev-export" className={CH_PAGE_NAV_LINK}>
          DATEV Export
        </Link>
        <Link href="/board/xrechnung-export" className={CH_PAGE_NAV_LINK}>
          XRechnung Export
        </Link>
      </div>

      <p className="mb-6 text-sm text-slate-600">
        Self-hosted n8n Workflow-Automatisierung (DSGVO-konform, EU-Region).
        Vorgefertigte Workflows für wiederkehrende Compliance-Aufgaben.
      </p>

      {/* ── Workflow Cards ── */}
      <div className="space-y-4">
        {WORKFLOWS.map((wf) => (
          <section key={wf.id} className={`${CH_CARD} space-y-3`}>
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="text-sm font-semibold text-slate-900">
                  {wf.name}
                </h3>
                <p className="mt-1 text-xs text-slate-500">
                  {wf.description}
                </p>
                <p className="mt-1 text-xs text-slate-400">
                  ⏰ {wf.schedule}
                </p>
              </div>
              <button
                onClick={() => handleTrigger(wf.type)}
                disabled={loading === wf.type}
                className={CH_BTN_SECONDARY}
              >
                {loading === wf.type ? "Triggering…" : "▶ Trigger"}
              </button>
            </div>
            {triggerResult[wf.type] && (
              <p className="text-xs text-slate-600">
                {triggerResult[wf.type]}
              </p>
            )}
          </section>
        ))}
      </div>

      {/* ── Info ── */}
      <section className={`${CH_CARD} mt-6 space-y-2`}>
        <p className={CH_SECTION_LABEL}>Hinweise</p>
        <ul className="list-inside list-disc space-y-1 text-sm text-slate-600">
          <li>
            Alle Workflows laufen self-hosted in der EU-Region (keine Daten an
            externe Cloud)
          </li>
          <li>
            Webhook-Authentifizierung über HMAC-SHA256-Signatur
          </li>
          <li>
            Workflow-Definitionen als JSON in{" "}
            <code className="rounded bg-slate-100 px-1 py-0.5 text-xs">
              infra/n8n/workflows/
            </code>
          </li>
          <li>
            Alle Ausführungen werden im Audit-Log protokolliert
          </li>
        </ul>
      </section>
    </div>
  );
}
