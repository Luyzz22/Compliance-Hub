import React from "react";
import Link from "next/link";

import { IncidentsBoardClient } from "@/components/board/IncidentsBoardClient";
import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import {
  fetchIncidentOverview,
  fetchIncidentsBySystem,
  type AIIncidentBySystem,
  type AIIncidentOverview,
} from "@/lib/api";
import { BOARD_PAGE_ROOT_CLASS, CH_PAGE_NAV_LINK } from "@/lib/boardLayout";

export default async function IncidentsPage() {
  let overview: AIIncidentOverview | null = null;
  let bySystem: AIIncidentBySystem[] = [];

  try {
    overview = await fetchIncidentOverview();
  } catch (error) {
    console.error("Incident overview API error:", error);
  }

  if (overview) {
    try {
      bySystem = await fetchIncidentsBySystem();
    } catch (error) {
      console.error("Incidents by system API error:", error);
    }
  }

  if (!overview) {
    return (
      <div className={BOARD_PAGE_ROOT_CLASS}>
        <EnterprisePageHeader
          title="Incidents"
          description="NIS2 Art. 21/23 · ISO 42001 Incident Management – mandantenbezogenes Incident-Register und KPIs."
          below={
            <>
              <Link href="/board/incidents" className={CH_PAGE_NAV_LINK}>
                Board: Incidents
              </Link>
              <Link href="/tenant/ai-systems" className={CH_PAGE_NAV_LINK}>
                KI-Systeme
              </Link>
            </>
          }
        />
        <div
          role="status"
          className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
        >
          Incident-KPIs konnten nicht geladen werden. Bitte versuchen Sie es später erneut oder
          wenden Sie sich an das AI-Governance-Team.
        </div>
      </div>
    );
  }

  return (
    <div className={BOARD_PAGE_ROOT_CLASS}>
      <EnterprisePageHeader
        title="Incidents"
        description="Globales Incident-Register mit gleichen Kennzahlen wie im Board – für Betrieb, ISB und Vorstand. NIS2 Art. 21/23 · ISO 42001."
        below={
          <>
            <Link href="/board/incidents" className={CH_PAGE_NAV_LINK}>
              Board: Incidents
            </Link>
            <Link href="/board/kpis" className={CH_PAGE_NAV_LINK}>
              Board KPIs
            </Link>
            <Link href="/tenant/ai-systems" className={CH_PAGE_NAV_LINK}>
              KI-Systeme
            </Link>
          </>
        }
      />

      <IncidentsBoardClient overview={overview} bySystem={bySystem} />
    </div>
  );
}
