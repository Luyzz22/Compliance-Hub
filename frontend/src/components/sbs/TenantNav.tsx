"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import React, { useMemo, useState } from "react";

import { useAiActEvidenceNav } from "@/hooks/useAiActEvidenceNav";
import {
  featureAiGovernancePlaybook,
  featureAiGovernanceSetupWizard,
  featureCrossRegulationDashboard,
  featurePilotRunbook,
} from "@/lib/config";

type NavItem = {
  href: string;
  label: string;
  keywords?: string;
};

type NavGroup = {
  label: string;
  items: NavItem[];
};

const navGroups: NavGroup[] = [
  {
    label: "Steuerung",
    items: [
      { href: "/tenant/compliance-overview", label: "Mandant & Übersicht", keywords: "home status" },
      { href: "/tenant/control-center", label: "Enterprise Control Center", keywords: "prioritäten fristen blocker" },
      { href: "/tenant/governance/overview", label: "Risk & Control Overview", keywords: "risiko kontrollen" },
      { href: "/tenant/governance/controls", label: "Unified Controls", keywords: "kontrollbibliothek" },
      { href: "/tenant/governance/compass", label: "Compliance Compass", keywords: "reife posture" },
    ],
  },
  {
    label: "Assessments",
    items: [
      { href: "/tenant/eu-ai-act", label: "EU AI Act", keywords: "ki verordnung readiness" },
      { href: "/tenant/transparency-assurance", label: "Transparency Assurance", keywords: "artikel 50 transparenz" },
      { href: "/tenant/impact-assessments", label: "DSFA & FRIA", keywords: "dpia datenschutz folgenabschätzung grundrechte artikel 27 35" },
      { href: "/tenant/ai-act/self-assessments", label: "Self-Assessment (AI Act)", keywords: "fragebogen" },
      { href: "/tenant/nis2/wizard", label: "NIS2 / KRITIS Wizard", keywords: "cyber resilienz" },
      { href: "/tenant/ai-systems", label: "KI-Systeme", keywords: "register inventar" },
      ...(featureCrossRegulationDashboard()
        ? [{ href: "/tenant/cross-regulation-dashboard", label: "Cross-Regulation", keywords: "mapping regulatorik" }]
        : []),
    ],
  },
  {
    label: "Betrieb & Evidenz",
    items: [
      { href: "/tenant/governance/workflows", label: "Workflows & Tasks", keywords: "aufgaben freigaben" },
      { href: "/tenant/governance/remediation", label: "Remediation", keywords: "maßnahmen abhilfe" },
      { href: "/tenant/governance/operations", label: "Betrieb & Resilienz", keywords: "health service" },
      { href: "/tenant/governance/audits", label: "Audit Readiness", keywords: "prüfung" },
      { href: "/tenant/audit-log", label: "Audit & Evidence", keywords: "nachweise protokoll" },
      { href: "/tenant/policies", label: "Policies & Regeln", keywords: "richtlinien" },
    ],
  },
  {
    label: "Einführung",
    items: [
      ...(featureAiGovernancePlaybook()
        ? [{ href: "/tenant/ai-governance-playbook", label: "AI Governance Playbook", keywords: "einführung cadence" }]
        : []),
      ...(featureAiGovernanceSetupWizard()
        ? [{ href: "/tenant/ai-governance-setup", label: "AI Governance Setup", keywords: "onboarding" }]
        : []),
      ...(featurePilotRunbook()
        ? [{ href: "/tenant/pilot-runbook", label: "Pilot-Runbook", keywords: "pilot" }]
        : []),
      { href: "/tenant/onboarding-readiness", label: "Onboarding Readiness", keywords: "sso integration mandant" },
      { href: "/tenant/blueprints", label: "Blueprints", keywords: "sap datev connector" },
      { href: "/tenant/trust-center", label: "Trust Center", keywords: "assurance security" },
    ],
  },
];

type TenantNavProps = {
  workspaceTenantId: string;
};

function normalizeSearch(value: string): string {
  return value.trim().toLocaleLowerCase("de-DE");
}

export function TenantNav({ workspaceTenantId }: TenantNavProps) {
  const pathname = usePathname();
  const [query, setQuery] = useState("");
  const { visible, href: evidenceHref } = useAiActEvidenceNav(workspaceTenantId);
  const normalizedQuery = normalizeSearch(query);
  const visibleGroups = useMemo(
    () =>
      navGroups
        .map((group) => ({
          ...group,
          items: normalizedQuery
            ? group.items.filter((item) =>
                normalizeSearch(`${item.label} ${item.keywords ?? ""}`).includes(normalizedQuery),
              )
            : group.items,
        }))
        .filter((group) => group.items.length > 0),
    [normalizedQuery],
  );
  const evidenceVisible =
    visible &&
    (!normalizedQuery || normalizeSearch("EU AI Act Evidenz Nachweise").includes(normalizedQuery));

  return (
    <nav className="px-3 py-4 text-sm" aria-label="Tenant-Navigation">
      <div className="px-1">
        <label className="sr-only" htmlFor="tenant-nav-filter">
          Workspace-Navigation filtern
        </label>
        <div className="relative">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
            aria-hidden
          >
            <circle cx="11" cy="11" r="7" />
            <path d="m20 20-4-4" />
          </svg>
          <input
            id="tenant-nav-filter"
            type="search"
            className="min-h-11 w-full rounded-lg border border-slate-200 bg-slate-50 py-2 pl-9 pr-8 text-sm text-slate-900 placeholder:text-slate-400"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Navigation filtern"
            autoComplete="off"
          />
        </div>
      </div>

      <div className="mt-5 space-y-6">
        {visibleGroups.map((group) => (
          <section key={group.label} aria-labelledby={`tenant-nav-${group.label.replaceAll(" ", "-").toLowerCase()}`}>
            <h2
              id={`tenant-nav-${group.label.replaceAll(" ", "-").toLowerCase()}`}
              className="px-2 pb-2 text-[0.68rem] font-semibold text-slate-400"
            >
              {group.label}
            </h2>
            <ul className="space-y-1">
              {group.items.map((item) => {
                const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      aria-current={active ? "page" : undefined}
                      className={`flex min-h-11 items-center gap-2 rounded-lg px-2.5 py-2 no-underline transition-colors ${
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
                      <span>{item.label}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </section>
        ))}

        {evidenceVisible ? (
          <section aria-labelledby="tenant-nav-evidence">
            <h2 id="tenant-nav-evidence" className="px-2 pb-2 text-[0.68rem] font-semibold text-slate-400">
              Mandantenspezifische Evidenz
            </h2>
            <Link
              href={evidenceHref}
              aria-current={pathname === evidenceHref || pathname.startsWith(`${evidenceHref}/`) ? "page" : undefined}
              className={`flex min-h-11 items-center gap-2 rounded-lg px-2.5 py-2 no-underline transition-colors ${
                pathname === evidenceHref || pathname.startsWith(`${evidenceHref}/`)
                  ? "bg-slate-100 font-semibold text-[var(--sbs-navy-deep)]"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              }`}
            >
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--sbs-navy-mid)]" aria-hidden />
              EU AI Act Evidenz
            </Link>
          </section>
        ) : null}
      </div>

      {visibleGroups.length === 0 && !evidenceVisible ? (
        <p role="status" className="mx-1 mt-5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 text-xs leading-5 text-slate-600">
          Keine Navigation für „{query}“ gefunden.
        </p>
      ) : null}
    </nav>
  );
}
