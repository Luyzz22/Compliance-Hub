import React from "react";
import Link from "next/link";

import { IncidentsBoardClient } from "@/components/board/IncidentsBoardClient";
import {
  fetchIncidentOverview,
  fetchIncidentsBySystem,
  type AIIncidentBySystem,
  type AIIncidentOverview,
} from "@/lib/api";
import {
  BOARD_PAGE_ROOT_CLASS,
  CH_PAGE_SUB,
  CH_PAGE_TITLE,
} from "@/lib/boardLayout";

export default async function BoardIncidentsPage() {
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
        <header className="mb-8">
          <h1 className={CH_PAGE_TITLE}>Incidents</h1>
          <p className={CH_PAGE_SUB}>
            NIS2 Art. 21/23 · ISO 42001 Incident Management
          </p>
        </header>
        <div
          role="status"
          className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
        >
          Incident-KPIs konnten nicht geladen werden. Bitte versuchen Sie es
          später erneut oder wenden Sie sich an das AI-Governance-Team.
        </div>
        <p className="mt-4">
          <Link
            href="/board/kpis"
            className="text-sm font-semibold text-cyan-700 underline decoration-cyan-700/30 hover:text-cyan-900"
          >
            ← Zurück zu Board-KPIs
          </Link>
        </p>
      </div>
    );
  }

  return (
    <div className={BOARD_PAGE_ROOT_CLASS}>
      <header className="mb-8">
        <h1 className={CH_PAGE_TITLE}>Incidents</h1>
        <p className={CH_PAGE_SUB}>
          NIS2 Art. 21/23 (Incident &amp; Business Continuity) · ISO 42001 ·
          Standort Deutschland
        </p>
        <nav
          className="mt-4 flex flex-wrap gap-x-4 gap-y-2 text-sm font-medium"
          aria-label="Verwandte Board-Seiten"
        >
          <Link
            href="/board/kpis"
            className="rounded-lg text-cyan-700 underline decoration-cyan-700/30 underline-offset-4 hover:text-cyan-900"
          >
            Board KPIs
          </Link>
          <Link
            href="/board/nis2-kritis"
            className="rounded-lg text-cyan-700 underline decoration-cyan-700/30 underline-offset-4 hover:text-cyan-900"
          >
            NIS2 / KRITIS
          </Link>
        </nav>
      </header>

      <IncidentsBoardClient overview={overview} bySystem={bySystem} />
    </div>
  );
}
