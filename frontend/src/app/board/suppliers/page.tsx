import React from "react";
import Link from "next/link";

import {
  fetchSupplierRiskOverview,
  fetchSupplierRiskBySystem,
  type AISupplierRiskBySystem,
  type AISupplierRiskOverview,
} from "@/lib/api";

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
      <main className="sbs-page-main">
        <header className="mb-6">
          <h1 className="sbs-h1">
            AI Governance – Supplier-Risiko
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            NIS2 Art. 21/24 Supply-Chain-Security · KRITIS-Bezug
          </p>
        </header>
        <div
          role="status"
          className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800"
        >
          Supplier-Risiko-KPIs konnten nicht geladen werden. Bitte versuchen Sie
          es später erneut oder wenden Sie sich an das AI-Governance-Team.
        </div>
        <p className="mt-4">
          <Link
            href="/board/kpis"
            className="text-sm font-medium text-slate-600 underline hover:text-slate-900"
          >
            ← Zurück zu Board-KPIs
          </Link>
        </p>
      </main>
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
    <main className="sbs-page-main">
      <header className="mb-6">
        <h1 className="sbs-h1">
          AI Governance – Supplier-Risiko
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          NIS2 Art. 21/24 Supply-Chain-Security · Lieferanten-Risikoregister ·
          KRITIS-Bezug · Standort Deutschland
        </p>
        <p className="mt-2">
          <Link
            href="/board/kpis"
            className="text-sm font-medium text-slate-600 underline hover:text-slate-900"
            aria-label="Zurück zu Board-KPIs"
          >
            ← Zurück zu Board-KPIs
          </Link>
        </p>
      </header>

      <section
        aria-label="Supplier-Risiko-KPIs"
        className="mb-8 grid gap-4 md:grid-cols-2 lg:grid-cols-4"
      >
        <div className="sbs-panel flex flex-col p-4">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Systeme mit Lieferanten-Register
          </h2>
          <p className="mt-2 text-3xl font-semibold text-slate-900">
            {overview.total_systems_with_suppliers}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {coveragePercent} % der KI-Systeme mit dokumentiertem
            Lieferanten-Risikoregister
          </p>
        </div>
        <div className="sbs-panel flex flex-col p-4">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Systeme ohne Supplier-Risikoregister
          </h2>
          <p className="mt-2 text-3xl font-semibold text-slate-900">
            {overview.systems_without_supplier_risk_register}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            NIS2 Supply-Chain-Anforderung aktuell nicht erfüllt
          </p>
        </div>
        <div className="sbs-panel flex flex-col p-4">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Kritische KI-Systeme gesamt
          </h2>
          <p className="mt-2 text-3xl font-semibold text-slate-900">
            {overview.critical_suppliers_total}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Hohe/Sehr hohe Kritikalität (KRITIS-relevant)
          </p>
        </div>
        <div className="sbs-panel flex flex-col p-4">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Kritische ohne Lieferanten-Controls
          </h2>
          <p className="mt-2 text-3xl font-semibold text-slate-900">
            {overview.critical_suppliers_without_controls}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Handlungsbedarf für Supply-Chain-Sicherheit
          </p>
        </div>
      </section>

      <section
        aria-label="Supplier-Risiko nach Risikostufe"
        className="sbs-panel mb-8 p-4"
      >
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-700">
          KI-Systeme nach Supplier-Risikostufe
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs text-slate-500">
                <th className="pb-2 font-semibold">Risikostufe</th>
                <th className="pb-2 font-semibold">Mit Register</th>
                <th className="pb-2 font-semibold">Ohne Register</th>
              </tr>
            </thead>
            <tbody>
              {overview.by_risk_level.map((entry) => (
                <tr key={entry.risk_level} className="border-b border-slate-100">
                  <td className="py-2 font-medium text-slate-900">
                    {riskLevelLabel(entry.risk_level)}
                  </td>
                  <td className="py-2 text-slate-700">
                    {entry.systems_with_register}
                  </td>
                  <td className="py-2 text-slate-700">
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
          className="sbs-panel p-4"
        >
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-700">
            Top 3 KI-Systeme mit höchstem Supplier-Risiko
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-xs text-slate-500">
                  <th className="pb-2 font-semibold">KI-System</th>
                  <th className="pb-2 font-semibold">Lieferanten-Register</th>
                  <th className="pb-2 font-semibold">Risiko-Score</th>
                </tr>
              </thead>
              <tbody>
                {topSystems.map((row) => (
                  <tr key={row.ai_system_id} className="border-b border-slate-100">
                    <td className="py-2 font-medium text-slate-900">
                      {row.ai_system_name}
                    </td>
                    <td className="py-2 text-slate-700">
                      {row.has_supplier_risk_register ? "Ja" : "Nein"}
                    </td>
                    <td className="py-2 text-slate-700">
                      {row.supplier_risk_score.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </main>
  );
}
