import React from "react";
import Link from "next/link";

import {
  fetchSupplierRiskOverview,
  fetchSupplierRiskBySystem,
  type AISupplierRiskBySystem,
  type AISupplierRiskOverview,
} from "@/lib/api";
import { BoardToWorkspaceCtas } from "@/components/sbs/BoardToWorkspaceCtas";
import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import {
  BOARD_PAGE_ROOT_CLASS,
  CH_CARD,
  CH_PAGE_NAV_LINK,
  CH_SECTION_LABEL,
} from "@/lib/boardLayout";

function riskLevelLabel(level: string): string {
  const labels: Record<string, string> = {
    high: "Hoch",
    medium: "Mittel",
    low: "Niedrig",
  };
  return labels[level] ?? level;
}

export default async function BoardSuppliersPage() {
  let overview: AISupplierRiskOverview | null = null;
  let bySystem: AISupplierRiskBySystem[] = [];

  try {
    overview = await fetchSupplierRiskOverview();
  } catch (error) {
    console.error("Supplier risk overview API error:", error);
  }

  if (overview) {
    try {
      bySystem = await fetchSupplierRiskBySystem();
    } catch (error) {
      console.error("Supplier risk by system API error:", error);
    }
  }

  if (!overview) {
    return (
      <div className={BOARD_PAGE_ROOT_CLASS}>
        <EnterprisePageHeader
          eyebrow="Board"
          title="Supplier-Risiko"
          description="NIS2 Art. 21/24 Supply-Chain-Security · Lieferketten · KRITIS-Bezug"
          below={
            <Link href="/board/kpis" className={CH_PAGE_NAV_LINK}>
              Zurück zu Board KPIs
            </Link>
          }
        />
        <div
          role="status"
          className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
        >
          Supplier-Risiko-KPIs konnten nicht geladen werden. Bitte versuchen Sie
          es später erneut oder wenden Sie sich an das AI-Governance-Team.
        </div>
      </div>
    );
  }

  const topSystems = bySystem.filter((e) => e.supplier_risk_score > 0).slice(0, 3);
  const totalSystems =
    overview.total_systems_with_suppliers + overview.systems_without_supplier_risk_register;
  const coveragePercent =
    totalSystems > 0
      ? Math.round((overview.total_systems_with_suppliers / totalSystems) * 100)
      : 0;

  return (
    <div className={BOARD_PAGE_ROOT_CLASS}>
      <EnterprisePageHeader
        eyebrow="Board"
        title="Supplier-Risiko"
        description="NIS2 Art. 21/24 Supply-Chain-Security · Lieferanten-Risikoregister · KRITIS-Bezug · Standort Deutschland"
        below={
          <>
            <Link href="/board/kpis" className={CH_PAGE_NAV_LINK}>
              Board KPIs
            </Link>
            <Link href="/board/nis2-kritis" className={CH_PAGE_NAV_LINK}>
              NIS2 / KRITIS
            </Link>
            <Link href="/board/incidents" className={CH_PAGE_NAV_LINK}>
              Incidents
            </Link>
          </>
        }
      />

      <BoardToWorkspaceCtas />

      <section
        aria-label="Supplier-Risiko-KPIs"
        className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4"
      >
        <div className={`${CH_CARD} flex min-w-0 flex-col`}>
          <p className={CH_SECTION_LABEL}>Mit Lieferanten-Register</p>
          <p className="mt-2 text-3xl font-semibold text-slate-900">
            {overview.total_systems_with_suppliers}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {coveragePercent} % der KI-Systeme mit dokumentiertem
            Lieferanten-Risikoregister
          </p>
        </div>
        <div className={`${CH_CARD} flex min-w-0 flex-col`}>
          <p className={CH_SECTION_LABEL}>Ohne Supplier-Risikoregister</p>
          <p className="mt-2 text-3xl font-semibold text-slate-900">
            {overview.systems_without_supplier_risk_register}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            NIS2 Supply-Chain-Anforderung aktuell nicht erfüllt
          </p>
        </div>
        <div className={`${CH_CARD} flex min-w-0 flex-col`}>
          <p className={CH_SECTION_LABEL}>Kritische KI-Systeme gesamt</p>
          <p className="mt-2 text-3xl font-semibold text-slate-900">
            {overview.critical_suppliers_total}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Hohe/Sehr hohe Kritikalität (KRITIS-relevant)
          </p>
        </div>
        <div className={`${CH_CARD} flex min-w-0 flex-col`}>
          <p className={CH_SECTION_LABEL}>Kritisch ohne Lieferanten-Controls</p>
          <p className="mt-2 text-3xl font-semibold text-slate-900">
            {overview.critical_suppliers_without_controls}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Handlungsbedarf für Supply-Chain-Sicherheit
          </p>
        </div>
      </section>

      <section aria-label="Supplier-Risiko nach Risikostufe" className={`${CH_CARD} mb-8`}>
        <h2 className="text-base font-semibold text-slate-900">
          KI-Systeme nach Supplier-Risikostufe
        </h2>
        <div className="mt-4 overflow-x-auto rounded-xl border border-slate-100">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/80 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                <th className="px-4 py-3">Risikostufe</th>
                <th className="px-4 py-3">Mit Register</th>
                <th className="px-4 py-3">Ohne Register</th>
              </tr>
            </thead>
            <tbody>
              {overview.by_risk_level.map((entry) => (
                <tr
                  key={entry.risk_level}
                  className="border-b border-slate-100 transition hover:bg-cyan-50/40"
                >
                  <td className="px-4 py-3 font-semibold text-slate-900">
                    {riskLevelLabel(entry.risk_level)}
                  </td>
                  <td className="px-4 py-3 tabular-nums text-slate-700">
                    {entry.systems_with_register}
                  </td>
                  <td className="px-4 py-3 tabular-nums text-slate-700">
                    {entry.systems_without_register}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {topSystems.length > 0 && (
        <section
          aria-label="Top-KI-Systeme mit höchstem Supplier-Risiko"
          className={CH_CARD}
        >
          <h2 className="text-base font-semibold text-slate-900">
            Top 3 KI-Systeme mit höchstem Supplier-Risiko
          </h2>
          <div className="mt-4 overflow-x-auto rounded-xl border border-slate-100">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/80 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  <th className="px-4 py-3">KI-System</th>
                  <th className="px-4 py-3">Lieferanten-Register</th>
                  <th className="px-4 py-3">Risiko-Score</th>
                </tr>
              </thead>
              <tbody>
                {topSystems.map((row) => (
                  <tr
                    key={row.ai_system_id}
                    className="border-b border-slate-100 transition hover:bg-cyan-50/40"
                  >
                    <td className="px-4 py-3 font-semibold text-slate-900">
                      {row.ai_system_name}
                    </td>
                    <td className="px-4 py-3 text-slate-700">
                      {row.has_supplier_risk_register ? "Ja" : "Nein"}
                    </td>
                    <td className="px-4 py-3 tabular-nums text-slate-700">
                      {row.supplier_risk_score.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
