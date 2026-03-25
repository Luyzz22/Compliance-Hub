import Link from "next/link";
import { notFound } from "next/navigation";
import React from "react";

import { CrossRegulationDashboardClient } from "@/app/tenant/cross-regulation-dashboard/CrossRegulationDashboardClient";
import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import {
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_SECTION_LABEL,
  CH_SHELL,
} from "@/lib/boardLayout";
import {
  fetchCrossRegulationSummary,
  fetchRegulatoryControls,
  fetchRegulatoryRequirements,
  fetchTenantAiGovernanceSetup,
} from "@/lib/api";
import {
  featureAiGovernanceSetupWizard,
  featureCrossRegulationDashboard,
  featureCrossRegulationLlmAssist,
} from "@/lib/config";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

export default async function CrossRegulationDashboardPage() {
  if (!featureCrossRegulationDashboard()) {
    notFound();
  }

  const tenantId = await getWorkspaceTenantIdServer();

  let summary: Awaited<ReturnType<typeof fetchCrossRegulationSummary>> | null = null;
  let requirements: Awaited<ReturnType<typeof fetchRegulatoryRequirements>> = [];
  let controls: Awaited<ReturnType<typeof fetchRegulatoryControls>> = [];
  let loadError: string | null = null;

  try {
    ;[summary, requirements, controls] = await Promise.all([
      fetchCrossRegulationSummary(tenantId),
      fetchRegulatoryRequirements(tenantId),
      fetchRegulatoryControls(tenantId),
    ]);
  } catch (e) {
    loadError = e instanceof Error ? e.message : "API-Fehler";
  }

  let preferredFrameworkKeys: string[] | undefined;
  if (featureAiGovernanceSetupWizard() && !loadError && summary) {
    try {
      const ags = await fetchTenantAiGovernanceSetup(tenantId);
      if (ags.active_frameworks?.length) {
        preferredFrameworkKeys = ags.active_frameworks;
      }
    } catch {
      preferredFrameworkKeys = undefined;
    }
  }

  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        eyebrow="Tenant"
        title="Cross-Regulation Dashboard"
        description="Pflichten mehrerer Regelwerke, tenant-spezifische Controls und Coverage – Grundlage für „Map once, comply many“."
        actions={
          <>
            <Link href="/tenant/compliance-overview" className={`${CH_BTN_SECONDARY} text-sm`}>
              Zur Übersicht
            </Link>
            <Link href="/tenant/ai-governance-playbook" className={`${CH_BTN_SECONDARY} text-sm`}>
              AI Governance Playbook
            </Link>
          </>
        }
      />

      <p className="mb-6 text-sm text-slate-500">
        Mandant: <span className="font-mono font-semibold text-slate-800">{tenantId}</span>
      </p>

      {loadError ? (
        <section className={CH_CARD} aria-label="Fehler">
          <p className={CH_SECTION_LABEL}>Daten nicht geladen</p>
          <p className="mt-2 text-sm text-rose-800">{loadError}</p>
          <p className="mt-2 text-xs text-slate-600">
            Prüfen Sie API-Basis-URL, API-Key und ob{" "}
            <code className="rounded bg-slate-100 px-1">COMPLIANCEHUB_FEATURE_CROSS_REGULATION_DASHBOARD</code>{" "}
            aktiv ist.
          </p>
        </section>
      ) : summary ? (
        <CrossRegulationDashboardClient
          tenantId={tenantId}
          summary={summary.frameworks}
          requirements={requirements}
          controls={controls}
          llmAssistEnabled={featureCrossRegulationLlmAssist()}
          preferredFrameworkKeys={preferredFrameworkKeys}
        />
      ) : null}
    </div>
  );
}
