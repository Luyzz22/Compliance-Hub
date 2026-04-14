import React from "react";
import Link from "next/link";

import { fetchGapReports, type GapReportSummary } from "@/lib/api";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";
import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import {
  BOARD_PAGE_ROOT_CLASS,
  CH_CARD,
  CH_CARD_MUTED,
  CH_PAGE_NAV_LINK,
  CH_SECTION_LABEL,
} from "@/lib/boardLayout";

/* ── Status badge ──────────────────────────────────────────────────── */

function statusBadge(status: string): { label: string; cls: string } {
  switch (status) {
    case "completed":
      return {
        label: "Abgeschlossen",
        cls: "bg-emerald-100 text-emerald-900",
      };
    case "running":
      return { label: "Läuft", cls: "bg-blue-100 text-blue-900" };
    case "failed":
      return { label: "Fehlgeschlagen", cls: "bg-red-100 text-red-900" };
    default:
      return { label: "Ausstehend", cls: "bg-slate-100 text-slate-700" };
  }
}

/* ── Page ──────────────────────────────────────────────────────────── */

export default async function GapAnalysisPage() {
  const tenantId = await getWorkspaceTenantIdServer();
  let reports: GapReportSummary[] = [];

  try {
    reports = await fetchGapReports(tenantId);
  } catch (error) {
    console.error("Gap Analysis API error:", error);
  }

  return (
    <div className={BOARD_PAGE_ROOT_CLASS}>
      <EnterprisePageHeader
        eyebrow="Enterprise"
        title="Gap-Analyse (RAG)"
        description="KI-gestützte Compliance-Lückenanalyse auf Artikel-Ebene — EU AI Act, ISO 42001, NIS2, DSGVO."
        below={
          <>
            <Link
              href="/board/executive-dashboard"
              className={CH_PAGE_NAV_LINK}
            >
              Executive Dashboard
            </Link>
            <Link href="/board/datev-export" className={CH_PAGE_NAV_LINK}>
              DATEV Export
            </Link>
            <Link href="/board/kpis" className={CH_PAGE_NAV_LINK}>
              Board KPIs
            </Link>
          </>
        }
      />

      {/* ── Info Banner ── */}
      <section className={`${CH_CARD_MUTED} mb-6`}>
        <p className="text-sm text-slate-600">
          Die Gap-Analyse nutzt eine RAG-Pipeline (pgvector) über
          regulatorische Texte (EU AI Act, ISO 42001, NIS2-UmSG, DSGVO).
          Lücken werden auf Artikel-Ebene identifiziert, nach Bußgeldrisiko
          priorisiert und mit Maßnahmenempfehlungen versehen.
        </p>
        <p className="mt-2 text-xs text-slate-400">
          LLM: Multi-Model-Router (primär Claude Sonnet 4) ·
          LangSmith-Tracing aktiv · Keine personenbezogenen Daten im Prompt
        </p>
      </section>

      {/* ── Report List ── */}
      <section aria-label="Gap Reports" className="mb-8">
        <div className="flex items-center justify-between">
          <p className={CH_SECTION_LABEL}>Gap-Reports</p>
        </div>

        {reports.length === 0 ? (
          <div className={`${CH_CARD} mt-3 text-sm text-slate-500`}>
            Noch keine Gap-Analyse durchgeführt. Starten Sie eine Analyse über
            die API oder den Button oben.
          </div>
        ) : (
          <div className="mt-3 space-y-3">
            {reports.map((r) => {
              const badge = statusBadge(r.status);
              return (
                <div key={r.id} className={CH_CARD}>
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span
                          className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${badge.cls}`}
                        >
                          {badge.label}
                        </span>
                        <span className="text-xs text-slate-400">
                          {r.created_at?.slice(0, 16).replace("T", " ") ??
                            "–"}
                        </span>
                      </div>
                      <p className="mt-1 text-sm font-semibold text-slate-900">
                        Normen:{" "}
                        {r.norm_scope
                          .split(",")
                          .map((n) => n.trim().replace(/_/g, " ").toUpperCase())
                          .join(", ")}
                      </p>
                      {r.summary && (
                        <p className="mt-1 line-clamp-2 text-xs text-slate-500">
                          {r.summary}
                        </p>
                      )}
                    </div>
                    {r.completed_at && (
                      <span className="whitespace-nowrap text-xs text-slate-400">
                        Abgeschlossen:{" "}
                        {r.completed_at.slice(0, 16).replace("T", " ")}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* ── Cross-Norm Mapping Hint ── */}
      <section className={`${CH_CARD_MUTED} mb-6`}>
        <p className={CH_SECTION_LABEL}>Map Once, Comply Many</p>
        <p className="mt-2 text-sm text-slate-600">
          Die Gap-Analyse identifiziert automatisch Querverweise zwischen
          Normen. Beispiel: ISO 42001 Annex A.6 (Risikomanagement) deckt
          weitgehend EU AI Act Art. 9 Abs. 2 ab. Maßnahmen können
          normenübergreifend zugeordnet werden.
        </p>
      </section>
    </div>
  );
}
