"use client";

import { useCallback, useEffect, useState } from "react";
import {
  CH_CARD,
  CH_CARD_MUTED,
  CH_SHELL,
  CH_PAGE_TITLE,
  CH_PAGE_SUB,
  CH_SECTION_LABEL,
  CH_BADGE,
  CH_BTN_PRIMARY,
  CH_SKELETON,
} from "@/lib/boardLayout";
import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface KpiSummary {
  compliance_score: { score: number; total_controls: number; implemented_controls: number };
  open_risks: number;
  trust_center_accesses: number;
  upcoming_deadlines: { date: string; framework: string }[];
}

interface FrameworkCoverage {
  framework: string;
  framework_key: string;
  total_requirements: number;
  covered: number;
  partial: number;
  planned: number;
  not_applicable: number;
}

interface RiskMatrix {
  critical: number;
  high: number;
  medium: number;
  low: number;
  total: number;
}

interface ActivityEntry {
  id: number;
  actor: string;
  action: string;
  entity_type: string;
  entity_id: string;
  created_at: string | null;
  outcome: string | null;
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";
const TENANT_ID = process.env.NEXT_PUBLIC_TENANT_ID || "tenant-overview-001";

function apiHeaders(): Record<string, string> {
  return {
    "x-api-key": API_KEY,
    "x-tenant-id": TENANT_ID,
    "x-opa-user-role": "compliance_admin",
    "Content-Type": "application/json",
  };
}

async function fetchJson<T>(path: string): Promise<T | null> {
  try {
    const resp = await fetch(`${API_BASE}${path}`, { headers: apiHeaders() });
    if (!resp.ok) return null;
    return (await resp.json()) as T;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// KPI Card
// ---------------------------------------------------------------------------

function KpiCard({
  label,
  value,
  sub,
  color = "text-slate-900",
}: {
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
}) {
  return (
    <div className={CH_CARD}>
      <p className={CH_SECTION_LABEL}>{label}</p>
      <p className={`mt-2 text-3xl font-bold tracking-tight ${color}`}>{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Framework Coverage Bar
// ---------------------------------------------------------------------------

function CoverageBar({ fw }: { fw: FrameworkCoverage }) {
  const total = fw.total_requirements || 1;
  const pctCovered = Math.round((fw.covered / total) * 100);
  const pctPartial = Math.round((fw.partial / total) * 100);
  const pctPlanned = Math.round((fw.planned / total) * 100);

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-slate-800">{fw.framework}</span>
        <span className="text-xs text-slate-500">
          {fw.covered}/{fw.total_requirements} Anforderungen
        </span>
      </div>
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-slate-100">
        {pctCovered > 0 && (
          <div className="bg-emerald-500 transition-all" style={{ width: `${pctCovered}%` }} />
        )}
        {pctPartial > 0 && (
          <div className="bg-amber-400 transition-all" style={{ width: `${pctPartial}%` }} />
        )}
        {pctPlanned > 0 && (
          <div className="bg-slate-300 transition-all" style={{ width: `${pctPlanned}%` }} />
        )}
      </div>
      <div className="flex gap-3 text-[0.65rem] text-slate-500">
        <span>🟢 Vollständig {fw.covered}</span>
        <span>🟡 Teilweise {fw.partial}</span>
        <span>⬜ Geplant {fw.planned}</span>
        <span>➖ N/A {fw.not_applicable}</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Risk Matrix Heatmap
// ---------------------------------------------------------------------------

function RiskMatrixGrid({ matrix }: { matrix: RiskMatrix }) {
  const cells = [
    { label: "Kritisch", count: matrix.critical, bg: "bg-red-500 text-white" },
    { label: "Hoch", count: matrix.high, bg: "bg-orange-400 text-white" },
    { label: "Mittel", count: matrix.medium, bg: "bg-amber-300 text-amber-900" },
    { label: "Niedrig", count: matrix.low, bg: "bg-emerald-200 text-emerald-900" },
  ];

  return (
    <div className="grid grid-cols-2 gap-2">
      {cells.map((c) => (
        <div
          key={c.label}
          className={`flex flex-col items-center justify-center rounded-xl p-4 ${c.bg}`}
        >
          <span className="text-2xl font-bold">{c.count}</span>
          <span className="text-xs font-medium">{c.label}</span>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Activity Feed
// ---------------------------------------------------------------------------

function ActivityFeed({ entries }: { entries: ActivityEntry[] }) {
  if (entries.length === 0) {
    return <p className="text-sm text-slate-500">Keine Aktivitäten vorhanden.</p>;
  }

  return (
    <ul className="divide-y divide-slate-100">
      {entries.map((e) => (
        <li key={e.id} className="flex items-start gap-3 py-2.5">
          <span className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-cyan-500" />
          <div className="min-w-0 flex-1">
            <p className="text-sm text-slate-800">
              <strong>{e.actor}</strong> · {e.action}
            </p>
            <p className="truncate text-xs text-slate-500">
              {e.entity_type} / {e.entity_id}
              {e.created_at && ` · ${new Date(e.created_at).toLocaleString("de-DE")}`}
            </p>
          </div>
          {e.outcome && (
            <span
              className={`${CH_BADGE} ${
                e.outcome === "success"
                  ? "bg-emerald-50 text-emerald-700 ring-emerald-200"
                  : "bg-red-50 text-red-700 ring-red-200"
              }`}
            >
              {e.outcome}
            </span>
          )}
        </li>
      ))}
    </ul>
  );
}

// ---------------------------------------------------------------------------
// Framework Ampel
// ---------------------------------------------------------------------------

function FrameworkAmpel({ frameworks }: { frameworks: FrameworkCoverage[] }) {
  return (
    <div className="space-y-2">
      {frameworks.map((fw) => {
        const ratio = fw.total_requirements > 0 ? fw.covered / fw.total_requirements : 0;
        let dot = "🔴";
        let statusLabel = "Kritisch";
        if (ratio >= 0.75) {
          dot = "🟢";
          statusLabel = "Konform";
        } else if (ratio >= 0.3) {
          dot = "🟡";
          statusLabel = "In Arbeit";
        }

        return (
          <div
            key={fw.framework_key}
            className="flex items-center justify-between rounded-lg border border-slate-100 p-3"
          >
            <span className="text-sm font-medium text-slate-800">
              {dot} {fw.framework}
            </span>
            <span className="text-xs text-slate-500">{statusLabel}</span>
          </div>
        );
      })}
      {frameworks.length === 0 && (
        <p className="text-sm text-slate-500">Keine Frameworks konfiguriert.</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function ComplianceAnalyticsPage() {
  const [kpi, setKpi] = useState<KpiSummary | null>(null);
  const [frameworks, setFrameworks] = useState<FrameworkCoverage[]>([]);
  const [riskMatrix, setRiskMatrix] = useState<RiskMatrix | null>(null);
  const [activity, setActivity] = useState<ActivityEntry[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    setLoading(true);
    const [kpiData, fwData, riskData, feedData] = await Promise.all([
      fetchJson<KpiSummary>("/api/v1/analytics/kpi-summary?period_days=30"),
      fetchJson<FrameworkCoverage[]>("/api/v1/analytics/framework-coverage"),
      fetchJson<RiskMatrix>("/api/v1/analytics/risk-matrix"),
      fetchJson<ActivityEntry[]>("/api/v1/analytics/activity-feed?limit=10"),
    ]);
    if (kpiData) setKpi(kpiData);
    if (fwData) setFrameworks(fwData);
    if (riskData) setRiskMatrix(riskData);
    if (feedData) setActivity(feedData);
    setLoading(false);
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        eyebrow="Reporting"
        title="Compliance Analytics"
        breadcrumbs={[
          { label: "Board", href: "/board/kpis" },
          { label: "Compliance Analytics" },
        ]}
      />

      <p className={CH_PAGE_SUB}>
        Zentrale KPI-Übersicht für datengetriebene Compliance-Entscheidungen. Alle Metriken werden
        alle 5 Minuten aktualisiert.
      </p>

      {/* KPI Widgets */}
      {loading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className={`${CH_SKELETON} h-28`} />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard
            label="Compliance-Score"
            value={`${kpi?.compliance_score.score ?? 0}%`}
            sub={`${kpi?.compliance_score.implemented_controls ?? 0} von ${kpi?.compliance_score.total_controls ?? 0} Controls`}
            color={
              (kpi?.compliance_score.score ?? 0) >= 75
                ? "text-emerald-700"
                : (kpi?.compliance_score.score ?? 0) >= 50
                  ? "text-amber-700"
                  : "text-red-700"
            }
          />
          <KpiCard
            label="Offene Risiken"
            value={kpi?.open_risks ?? 0}
            sub="Kritisch + Hoch"
            color={
              (kpi?.open_risks ?? 0) > 0 ? "text-red-600" : "text-emerald-700"
            }
          />
          <KpiCard
            label="Trust Center Zugriffe"
            value={kpi?.trust_center_accesses ?? 0}
            sub="Letzte 30 Tage"
          />
          <KpiCard
            label="Nächste Fristen"
            value={kpi?.upcoming_deadlines.length ?? 0}
            sub="Anstehende Deadlines"
          />
        </div>
      )}

      {/* Middle: Coverage + Risk */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Coverage Chart */}
        <div className={`${CH_CARD} lg:col-span-2`}>
          <p className={CH_SECTION_LABEL}>Controls-Abdeckung pro Framework</p>
          <div className="mt-4 space-y-4">
            {loading ? (
              <div className={`${CH_SKELETON} h-40`} />
            ) : frameworks.length > 0 ? (
              frameworks.map((fw) => <CoverageBar key={fw.framework_key} fw={fw} />)
            ) : (
              <p className="text-sm text-slate-500">
                Keine Framework-Daten vorhanden. Erstellen Sie Controls und verknüpfen Sie diese mit
                Frameworks.
              </p>
            )}
          </div>
        </div>

        {/* Risk Matrix */}
        <div className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Risiko-Matrix</p>
          <div className="mt-4">
            {loading ? (
              <div className={`${CH_SKELETON} h-40`} />
            ) : riskMatrix ? (
              <>
                <RiskMatrixGrid matrix={riskMatrix} />
                <p className="mt-3 text-center text-xs text-slate-500">
                  {riskMatrix.total} offene Findings
                </p>
              </>
            ) : (
              <p className="text-sm text-slate-500">Keine Risikodaten verfügbar.</p>
            )}
          </div>
        </div>
      </div>

      {/* Bottom: Activity Feed + Framework Ampel */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className={`${CH_CARD} lg:col-span-2`}>
          <p className={CH_SECTION_LABEL}>Aktivitäts-Feed</p>
          <div className="mt-3">
            {loading ? (
              <div className={`${CH_SKELETON} h-48`} />
            ) : (
              <ActivityFeed entries={activity} />
            )}
          </div>
        </div>

        <div className={CH_CARD}>
          <p className={CH_SECTION_LABEL}>Framework-Ampel</p>
          <div className="mt-3">
            {loading ? (
              <div className={`${CH_SKELETON} h-40`} />
            ) : (
              <FrameworkAmpel frameworks={frameworks} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
