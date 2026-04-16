"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import React from "react";

import { useAiActEvidenceNav } from "@/hooks/useAiActEvidenceNav";
import {
  featureAiGovernancePlaybook,
  featureAiGovernanceSetupWizard,
  featureCrossRegulationDashboard,
  featurePilotRunbook,
} from "@/lib/config";

const baseItems = [
  { href: "/tenant/compliance-overview", label: "Mandant & Übersicht" },
  { href: "/tenant/governance/overview", label: "Risk & Control Overview" },
  { href: "/tenant/eu-ai-act", label: "EU AI Act" },
  { href: "/tenant/ai-act/self-assessments", label: "Self-Assessment (AI Act)" },
  { href: "/tenant/nis2/wizard", label: "NIS2 / KRITIS Wizard" },
  { href: "/tenant/ai-systems", label: "KI-Systeme" },
  { href: "/tenant/policies", label: "Policies & Regeln" },
  { href: "/tenant/audit-log", label: "Audit & Evidence" },
  { href: "/tenant/blueprints", label: "Blueprints" },
  { href: "/tenant/trust-center", label: "Trust Center" },
];

const items = [
  ...baseItems.slice(0, 1),
  ...(featureAiGovernancePlaybook()
    ? [{ href: "/tenant/ai-governance-playbook" as const, label: "AI Governance Playbook" }]
    : []),
  ...(featureAiGovernanceSetupWizard()
    ? [{ href: "/tenant/ai-governance-setup" as const, label: "AI Governance Setup" }]
    : []),
  ...(featureCrossRegulationDashboard()
    ? [{ href: "/tenant/cross-regulation-dashboard" as const, label: "Cross-Regulation" }]
    : []),
  ...(featurePilotRunbook()
    ? [{ href: "/tenant/pilot-runbook" as const, label: "Pilot-Runbook" }]
    : []),
  ...baseItems.slice(1),
];

type TenantNavProps = {
  workspaceTenantId: string;
};

export function TenantNav({ workspaceTenantId }: TenantNavProps) {
  const pathname = usePathname();
  const { visible, href: evidenceHref } = useAiActEvidenceNav(workspaceTenantId);
  return (
    <nav
      className="space-y-1 px-3 py-4 text-sm"
      aria-label="Tenant-Navigation"
    >
      <div className="px-2 pb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
        Arbeitsbereich
      </div>
      {items.map((item) => {
        const active =
          pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`flex items-center gap-2 rounded-lg px-2 py-2 no-underline transition ${
              active
                ? "bg-slate-100 font-semibold text-[var(--sbs-navy-deep)]"
                : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
            }`}
          >
            <span
              className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                active ? "bg-[var(--sbs-navy-mid)]" : "bg-slate-300"
              }`}
              aria-hidden
            />
            {item.label}
          </Link>
        );
      })}
      {visible ? (
        <>
          <div className="mt-4 px-2 pb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Compliance / Evidence
          </div>
          <Link
            href={evidenceHref}
            className={`flex items-center gap-2 rounded-lg px-2 py-2 no-underline transition ${
              pathname === evidenceHref || pathname.startsWith(`${evidenceHref}/`)
                ? "bg-slate-100 font-semibold text-[var(--sbs-navy-deep)]"
                : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
            }`}
          >
            <span
              className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                pathname === evidenceHref || pathname.startsWith(`${evidenceHref}/`)
                  ? "bg-[var(--sbs-navy-mid)]"
                  : "bg-slate-300"
              }`}
              aria-hidden
            />
            EU AI Act Evidenz
          </Link>
        </>
      ) : null}
    </nav>
  );
}
