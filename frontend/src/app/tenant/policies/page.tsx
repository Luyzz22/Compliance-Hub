import Link from "next/link";
import React from "react";

import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import {
  CH_BTN_PRIMARY,
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_PAGE_NAV_LINK,
  CH_SHELL,
} from "@/lib/boardLayout";

export default async function TenantPoliciesPage() {
  const policies: Record<string, unknown>[] = [];
  const rules: Record<string, unknown>[] = [];

  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        eyebrow="Tenant"
        title="Policy Engine"
        description={
          <>
            Zentrale Steuerung von Mandanten-Policies und Regeln für KI-Systeme – abgestimmt auf EU AI
            Act, NIS2 und ISO-Controls. Entscheidungen werden versioniert und für Audits nachvollziehbar
            gehalten.
          </>
        }
        actions={
          <>
            <button type="button" className={`${CH_BTN_SECONDARY} text-sm`}>
              Vorlagen
            </button>
            <button type="button" className={`${CH_BTN_PRIMARY} text-sm`}>
              Neue Policy
            </button>
          </>
        }
        below={
          <>
            <Link href="/tenant/audit-log" className={CH_PAGE_NAV_LINK}>
              Audit & Evidence
            </Link>
            <Link href="/tenant/ai-systems" className={CH_PAGE_NAV_LINK}>
              KI-System-Register
            </Link>
          </>
        }
      />

      <section className="grid gap-4 md:grid-cols-3">
        <div className={CH_CARD}>
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Policies
          </p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-slate-900">{policies.length}</p>
          <p className="mt-2 text-sm text-slate-600">Definierte Richtlinien im Mandanten</p>
        </div>
        <div className={CH_CARD}>
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Regeln</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-slate-900">{rules.length}</p>
          <p className="mt-2 text-sm text-slate-600">Ausführbare Checks (z. B. High-Risk → DPIA)</p>
        </div>
        <div className={CH_CARD}>
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Aktiv</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-emerald-700">
            {policies.length}
          </p>
          <p className="mt-2 text-sm text-slate-600">Policies mit aktivem Enforcement</p>
        </div>
      </section>

      <section className={`${CH_CARD} overflow-hidden p-0`}>
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200/80 px-5 py-4">
          <h2 className="text-sm font-semibold text-slate-900">Policies</h2>
          <button type="button" className={`${CH_BTN_SECONDARY} text-xs py-2`}>
            Neue Policy anlegen
          </button>
        </div>
        <div className="px-5 py-5 text-sm text-slate-600">
          <p>
            Die Policy-Liste erscheint hier, sobald die Policy-API angebunden ist. Geplant: Status,
            Owner, Gültigkeit, verknüpfte KI-Systeme und Mapping zu regulatorischen Anforderungen.
          </p>
        </div>
      </section>

      <section className={`${CH_CARD} overflow-hidden p-0`}>
        <div className="border-b border-slate-200/80 px-5 py-4">
          <h2 className="text-sm font-semibold text-slate-900">Regeln</h2>
        </div>
        <div className="px-5 py-5 text-sm text-slate-600">
          <p>
            Regel-Definitionen (z. B. „High-Risk erfordert DPIA“) folgen mit der Policy-Engine. Jede
            Regelausführung wird für GoBD-konforme Nachweise im Audit-Log protokolliert.
          </p>
        </div>
      </section>
    </div>
  );
}
