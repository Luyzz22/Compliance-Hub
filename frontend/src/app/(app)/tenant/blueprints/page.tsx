import Link from "next/link";
import React from "react";

import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import {
  CH_BTN_PRIMARY,
  CH_CARD,
  CH_PAGE_NAV_LINK,
  CH_SHELL,
} from "@/lib/boardLayout";

export default async function TenantBlueprintsPage() {
  const blueprints: { id: string; title: string; description: string }[] = [
    {
      id: "NIS2_BASELINE_MIDMARKET",
      title: "NIS2-Baseline für Mittelstand",
      description:
        "Basis-Set an Controls für NIS2 und ISO 27001 im DACH-Mittelstand – inkl. Lieferketten- und Incident-Fokus.",
    },
    {
      id: "AI_GOVERNANCE_STARTER",
      title: "AI Governance Starter",
      description:
        "High-Level AI-Governance für EU AI Act und ISO 42001: Rollen, Risikostufen und Nachweispfade.",
    },
  ];

  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        eyebrow="Tenant"
        title="Compliance Blueprints"
        description={
          <>
            Kuratierte Vorlagen für schnelles Onboarding: vorkonfigurierte Control-Sets und
            Governance-Strukturen, die Sie mandantenspezifisch aktivieren und erweitern können.
          </>
        }
        below={
          <>
            <Link href="/tenant/compliance-overview" className={CH_PAGE_NAV_LINK}>
              Mandanten-Übersicht
            </Link>
            <Link href="/tenant/eu-ai-act" className={CH_PAGE_NAV_LINK}>
              EU AI Act Cockpit
            </Link>
          </>
        }
      />

      <section className="grid gap-4 md:grid-cols-2">
        {blueprints.map((bp) => (
          <div key={bp.id} className={CH_CARD}>
            <p className="font-mono text-xs font-medium uppercase tracking-wide text-slate-500">
              {bp.id}
            </p>
            <h2 className="mt-2 text-base font-semibold text-slate-900">{bp.title}</h2>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">{bp.description}</p>
            <button type="button" className={`${CH_BTN_PRIMARY} mt-5 text-xs py-2`}>
              Blueprint aktivieren
            </button>
          </div>
        ))}
      </section>
    </div>
  );
}
