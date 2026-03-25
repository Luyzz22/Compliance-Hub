import Link from "next/link";
import React from "react";

import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import {
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_PAGE_NAV_LINK,
  CH_SHELL,
} from "@/lib/boardLayout";

export default async function TenantAuditLogPage() {
  const events: Record<string, unknown>[] = [];

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

      <section className={`${CH_CARD} overflow-hidden p-0`}>
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200/80 px-5 py-4">
          <h2 className="text-sm font-semibold text-slate-900">Chronologischer Audit-Log</h2>
          <button type="button" className={`${CH_BTN_SECONDARY} text-xs py-2`}>
            CSV exportieren
          </button>
        </div>
        <div className="px-5 py-5 text-sm text-slate-600">
          {events.length === 0 ? (
            <p>
              Sobald die Audit-APIs angebunden sind, erscheinen hier zeitgestempelte Ereignisse mit
              Akteur, Ressource und Korrelation zu Mandant und KI-System. Einträge sind append-only.
            </p>
          ) : (
            <p>{events.length} Einträge</p>
          )}
        </div>
      </section>

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
