"use client";

import React, { useEffect, useState } from "react";

import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import {
  fetchNis2KritisKpis,
  upsertNis2KritisKpi,
  type Nis2KritisKpiListResponse,
  type Nis2KritisKpiType,
} from "@/lib/api";
import {
  CH_BTN_PRIMARY,
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_SHELL,
} from "@/lib/boardLayout";

// ─── Types ───────────────────────────────────────────────────────────────────

type EURiskLevel = "prohibited" | "high_risk" | "limited_risk" | "minimal_risk";

interface ClassificationSummary {
  prohibited: number;
  high_risk: number;
  limited_risk: number;
  minimal_risk: number;
  total: number;
}

interface SystemReadiness {
  ai_system_id: string;
  ai_system_name: string;
  risk_level: string;
  readiness_score: number;
  total_requirements: number;
  completed: number;
  in_progress: number;
  not_started: number;
}

interface ComplianceDashboard {
  tenant_id: string;
  overall_readiness: number;
  systems: SystemReadiness[];
  deadline: string;
  days_remaining: number;
  urgent_gaps: {
    ai_system_id: string;
    ai_system_name: string;
    requirement_id: string;
    requirement_name: string;
    article: string;
  }[];
}

interface ComplianceRequirement {
  id: string;
  article: string;
  name: string;
  description: string;
  applies_to: string[];
  weight: number;
}

interface ComplianceStatusEntry {
  ai_system_id: string;
  requirement_id: string;
  status: "not_started" | "in_progress" | "completed" | "not_applicable";
  evidence_notes?: string;
  last_updated: string;
  updated_by: string;
}

interface RiskClassification {
  ai_system_id: string;
  risk_level: EURiskLevel;
  classification_path: string;
  annex_iii_category?: number;
  annex_i_legislation?: string;
  is_safety_component: boolean;
  requires_third_party_assessment: boolean;
  exception_applies: boolean;
  exception_reason?: string;
  profiles_natural_persons: boolean;
  classification_rationale: string;
  classified_at: string;
  classified_by: string;
  confidence_score: number;
}

interface AISystem {
  id: string;
  name: string;
  business_unit?: string;
  risk_level?: string;
  ai_act_category?: string;
  status?: string;
}

// ─── API helpers (client-side) ───────────────────────────────────────────────

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "tenant-overview-key";
const TENANT_ID = process.env.NEXT_PUBLIC_TENANT_ID || "tenant-overview-001";

async function api(path: string, init?: RequestInit) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "x-api-key": API_KEY,
      "x-tenant-id": TENANT_ID,
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) return null;
  return res.json();
}

// ─── Helpers ────────────────────────────────────────────────────────────────

function cn(...values: (string | false | null | undefined)[]) {
  return values.filter(Boolean).join(" ");
}

const RISK_BADGE: Record<string, string> = {
  prohibited:
    "bg-red-50 text-red-900 border border-red-200",
  high_risk:
    "bg-rose-50 text-rose-900 border border-rose-200",
  limited_risk:
    "bg-amber-50 text-amber-900 border border-amber-200",
  minimal_risk:
    "bg-emerald-50 text-emerald-900 border border-emerald-200",
  unclassified: "bg-slate-100 text-slate-600 border border-slate-200",
};

const RISK_LABEL: Record<string, string> = {
  prohibited: "Verboten",
  high_risk: "Hochrisiko",
  limited_risk: "Begrenztes Risiko",
  minimal_risk: "Minimales Risiko",
  unclassified: "Nicht klassifiziert",
};

const STATUS_BADGE: Record<string, string> = {
  not_started: "bg-red-50 text-red-900 border border-red-200",
  in_progress: "bg-amber-50 text-amber-900 border border-amber-200",
  completed: "bg-emerald-50 text-emerald-900 border border-emerald-200",
  not_applicable: "bg-slate-100 text-slate-600 border border-slate-200",
};

const STATUS_LABEL: Record<string, string> = {
  not_started: "Nicht begonnen",
  in_progress: "In Bearbeitung",
  completed: "Abgeschlossen",
  not_applicable: "N/A",
};

const NIS2_KPI_LABEL: Record<Nis2KritisKpiType, string> = {
  INCIDENT_RESPONSE_MATURITY: "Incident-Response-Reife",
  SUPPLIER_RISK_COVERAGE: "Supplier-Risk-Coverage",
  OT_IT_SEGREGATION: "OT/IT-Segregation",
};

function nis2RecommendedPercent(
  kpiType: Nis2KritisKpiType,
  rec: Nis2KritisKpiListResponse["recommended"]
): number | null {
  if (!rec) return null;
  switch (kpiType) {
    case "INCIDENT_RESPONSE_MATURITY":
      return rec.incident_response_maturity_percent;
    case "SUPPLIER_RISK_COVERAGE":
      return rec.supplier_risk_coverage_percent;
    case "OT_IT_SEGREGATION":
      return rec.ot_it_segregation_percent;
    default:
      return null;
  }
}

// ─── Questionnaire Steps (Classification Wizard) ────────────────────────────

type WizardStep = 1 | 2 | 3 | 4 | 5;

const STEP_TITLES: Record<WizardStep, string> = {
  1: "Verbotene Praktiken",
  2: "Anhang I – Sicherheitskomponente",
  3: "Anhang III – Anwendungsbereich",
  4: "Art. 6(3) – Ausnahmen",
  5: "Transparenzpflichten",
};

// ─── Components ─────────────────────────────────────────────────────────────

function ProgressBar({ value, className }: { value: number; className?: string }) {
  return (
    <div className={cn("h-2 w-full rounded-full bg-slate-200", className)}>
      <div
        className="h-full rounded-full bg-emerald-500 transition-all"
        style={{ width: `${Math.round(value * 100)}%` }}
      />
    </div>
  );
}

function CircularProgress({ value, size = 80 }: { value: number; size?: number }) {
  const pct = Math.round(value * 100);
  const r = (size - 8) / 2;
  const c = 2 * Math.PI * r;
  const offset = c - (value * c);
  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={size} height={size}>
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke="#e2e8f0" strokeWidth={6}
        />
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke="#10b981" strokeWidth={6}
          strokeDasharray={c} strokeDashoffset={offset}
          strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
      <span className="absolute text-sm font-semibold text-emerald-800">
        {pct}%
      </span>
    </div>
  );
}

// ─── Main Page ──────────────────────────────────────────────────────────────

type View = "dashboard" | "wizard" | "gap";

export default function EUAIActPage() {
  const [view, setView] = useState<View>("dashboard");
  const [dashboard, setDashboard] = useState<ComplianceDashboard | null>(null);
  const [summary, setSummary] = useState<ClassificationSummary | null>(null);
  const [systems, setSystems] = useState<AISystem[]>([]);
  const [loading, setLoading] = useState(true);

  // Wizard state
  const [wizardSystemId, setWizardSystemId] = useState("");
  const [wizardStep, setWizardStep] = useState<WizardStep>(1);
  const [wizardData, setWizardData] = useState<Record<string, unknown>>({});
  const [wizardResult, setWizardResult] = useState<RiskClassification | null>(null);

  // Gap analysis state
  const [gapSystemId, setGapSystemId] = useState("");
  const [gapStatuses, setGapStatuses] = useState<ComplianceStatusEntry[]>([]);
  const [requirements, setRequirements] = useState<ComplianceRequirement[]>([]);
  const [nis2Kpis, setNis2Kpis] = useState<Nis2KritisKpiListResponse | null>(null);
  const [nis2Draft, setNis2Draft] = useState<
    Record<Nis2KritisKpiType, { value: number; evidence: string }>
  >({
    INCIDENT_RESPONSE_MATURITY: { value: 0, evidence: "" },
    SUPPLIER_RISK_COVERAGE: { value: 0, evidence: "" },
    OT_IT_SEGREGATION: { value: 0, evidence: "" },
  });
  const [nis2Saving, setNis2Saving] = useState<Nis2KritisKpiType | null>(null);

  const loadDashboard = async () => {
    setLoading(true);
    const [d, s, sys, reqs] = await Promise.all([
      api("/api/v1/compliance/dashboard"),
      api("/api/v1/classifications/summary"),
      api("/api/v1/ai-systems"),
      api("/api/v1/compliance/requirements"),
    ]);
    if (d) setDashboard(d);
    if (s) setSummary(s);
    if (sys) setSystems(sys);
    if (reqs) setRequirements(reqs);
    setLoading(false);
  };

  useEffect(() => {
    const id = setTimeout(() => void loadDashboard(), 0);
    return () => clearTimeout(id);
  }, []);

  const openWizard = (systemId: string) => {
    setWizardSystemId(systemId);
    setWizardStep(1);
    setWizardData({});
    setWizardResult(null);
    setView("wizard");
  };

  const openGap = async (systemId: string) => {
    setGapSystemId(systemId);
    const statuses = await api(`/api/v1/ai-systems/${systemId}/compliance`);
    if (statuses) setGapStatuses(statuses);
    try {
      const nis2 = await fetchNis2KritisKpis(systemId);
      setNis2Kpis(nis2);
      const types: Nis2KritisKpiType[] = [
        "INCIDENT_RESPONSE_MATURITY",
        "SUPPLIER_RISK_COVERAGE",
        "OT_IT_SEGREGATION",
      ];
      const nextDraft: Record<Nis2KritisKpiType, { value: number; evidence: string }> = {
        INCIDENT_RESPONSE_MATURITY: { value: 0, evidence: "" },
        SUPPLIER_RISK_COVERAGE: { value: 0, evidence: "" },
        OT_IT_SEGREGATION: { value: 0, evidence: "" },
      };
      for (const t of types) {
        const row = nis2.kpis.find((k) => k.kpi_type === t);
        nextDraft[t] = {
          value: row?.value_percent ?? 0,
          evidence: row?.evidence_ref ?? "",
        };
      }
      setNis2Draft(nextDraft);
    } catch {
      setNis2Kpis(null);
    }
    setView("gap");
  };

  const saveNis2Kpi = async (kpiType: Nis2KritisKpiType) => {
    const d = nis2Draft[kpiType];
    setNis2Saving(kpiType);
    try {
      const saved = await upsertNis2KritisKpi(gapSystemId, {
        kpi_type: kpiType,
        value_percent: Math.min(100, Math.max(0, Math.round(d.value))),
        evidence_ref: d.evidence.trim() || null,
        last_reviewed_at: new Date().toISOString(),
      });
      setNis2Kpis((prev) => {
        if (!prev) {
          return {
            kpis: [saved],
            recommended: null,
          };
        }
        const others = prev.kpis.filter((k) => k.kpi_type !== kpiType);
        return { ...prev, kpis: [...others, saved] };
      });
    } finally {
      setNis2Saving(null);
    }
  };

  const submitClassification = async () => {
    const result = await api(`/api/v1/ai-systems/${wizardSystemId}/classify`, {
      method: "POST",
      body: JSON.stringify(wizardData),
    });
    if (result) setWizardResult(result);
  };

  const updateStatus = async (
    requirementId: string,
    newStatus: string
  ) => {
    const result = await api(
      `/api/v1/ai-systems/${gapSystemId}/compliance/${requirementId}`,
      {
        method: "PUT",
        body: JSON.stringify({ status: newStatus }),
      }
    );
    if (result) {
      setGapStatuses((prev) =>
        prev.map((s) => (s.requirement_id === requirementId ? result : s))
      );
    }
  };

  // ─── Dashboard View ──────────────────────────────────────────────────────

  if (view === "dashboard") {
    return (
      <div className={CH_SHELL}>
        <EnterprisePageHeader
          eyebrow="Tenant"
          title="EU AI Act · Compliance"
          description="Risikoeinstufung, Klassifizierung und Lückenanalyse für alle KI-Systeme im Mandanten."
          actions={
            dashboard ? (
              <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-center shadow-sm">
                <div className="text-xs font-medium text-amber-900">Frist High-Risk</div>
                <div className="text-xl font-semibold tabular-nums text-amber-950">
                  {dashboard.days_remaining} Tage
                </div>
                <div className="text-[0.65rem] text-amber-800/90">bis 02.08.2026</div>
              </div>
            ) : null
          }
        />

        {loading ? (
          <div className="text-center text-slate-500 py-16">Laden…</div>
        ) : (
          <>
            {/* KPI Row */}
            <section className="grid gap-4 md:grid-cols-4">
              <div className={`${CH_CARD} p-5 text-center`}>
                <div className="text-xs font-medium text-slate-600">
                  Gesamtbereitschaft
                </div>
                <div className="mt-3 flex justify-center">
                  <CircularProgress value={dashboard?.overall_readiness ?? 0} />
                </div>
              </div>
              <div className={`${CH_CARD} p-5`}>
                <div className="text-xs font-medium text-slate-600">Verboten</div>
                <div className="mt-2 text-3xl font-semibold text-red-700">
                  {summary?.prohibited ?? 0}
                </div>
              </div>
              <div className={`${CH_CARD} p-5`}>
                <div className="text-xs font-medium text-slate-600">Hochrisiko</div>
                <div className="mt-2 text-3xl font-semibold text-rose-700">
                  {summary?.high_risk ?? 0}
                </div>
              </div>
              <div className={`${CH_CARD} p-5`}>
                <div className="text-xs font-medium text-slate-600">
                  Begrenztes / Minimales Risiko
                </div>
                <div className="mt-2 text-3xl font-semibold text-emerald-700">
                  {(summary?.limited_risk ?? 0) + (summary?.minimal_risk ?? 0)}
                </div>
              </div>
            </section>

            {/* Systems Table */}
            <section className={`${CH_CARD} overflow-hidden p-0`}>
              <div className="flex items-center justify-between border-b border-slate-200/80 px-5 py-4">
                <h2 className="text-sm font-semibold text-slate-900">AI-Systeme Übersicht</h2>
                <span className="text-xs text-slate-500">
                  {systems.length} Systeme
                </span>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="bg-slate-100 text-xs uppercase text-slate-600">
                    <tr>
                      <th className="px-5 py-2 font-medium">Name</th>
                      <th className="px-3 py-2 font-medium">Risikostufe</th>
                      <th className="px-3 py-2 font-medium">Bereitschaft</th>
                      <th className="px-3 py-2 font-medium">Aktionen</th>
                    </tr>
                  </thead>
                  <tbody>
                    {systems.map((sys) => {
                      const sr = dashboard?.systems.find(
                        (s) => s.ai_system_id === sys.id
                      );
                      const rl = sr?.risk_level || "unclassified";
                      return (
                        <tr
                          key={sys.id}
                          className="border-t border-slate-200/80 hover:bg-slate-50"
                        >
                          <td className="px-5 py-2">
                            <div className="font-medium text-slate-900">
                              {sys.name}
                            </div>
                            <div className="text-xs text-slate-500">{sys.id}</div>
                          </td>
                          <td className="px-3 py-2">
                            <span
                              className={cn(
                                "inline-flex rounded-full px-2 py-0.5 text-xs font-medium",
                                RISK_BADGE[rl] || RISK_BADGE.unclassified
                              )}
                            >
                              {RISK_LABEL[rl] || rl}
                            </span>
                          </td>
                          <td className="px-3 py-2 w-48">
                            {sr && sr.total_requirements > 0 ? (
                              <div>
                                <ProgressBar value={sr.readiness_score} />
                                <div className="mt-1 text-xs text-slate-600">
                                  {Math.round(sr.readiness_score * 100)}% –{" "}
                                  {sr.completed}/{sr.total_requirements} erledigt
                                </div>
                              </div>
                            ) : (
                              <span className="text-xs text-slate-500">–</span>
                            )}
                          </td>
                          <td className="px-3 py-2">
                            <div className="flex gap-2">
                              <button
                                onClick={() => openWizard(sys.id)}
                                className="rounded border border-slate-200 px-2 py-1 text-xs text-slate-900 hover:bg-slate-100"
                              >
                                Klassifizieren
                              </button>
                              <button
                                onClick={() => openGap(sys.id)}
                                className="rounded border border-slate-200 px-2 py-1 text-xs text-slate-900 hover:bg-slate-100"
                              >
                                Lückenanalyse
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                    {systems.length === 0 && (
                      <tr>
                        <td
                          colSpan={4}
                          className="px-5 py-6 text-center text-xs text-slate-500"
                        >
                          Keine AI-Systeme registriert.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>

            {/* Urgent Gaps */}
            {dashboard && dashboard.urgent_gaps.length > 0 && (
              <section className={`${CH_CARD} overflow-hidden p-0`}>
                <div className="border-b border-slate-200/80 px-5 py-4">
                  <h2 className="text-sm font-semibold text-slate-900">
                    Dringendste Lücken (Top 3)
                  </h2>
                </div>
                <div className="space-y-3 p-5">
                  {dashboard.urgent_gaps.map((gap, i) => (
                    <div
                      key={i}
                      className="rounded-xl border border-rose-200 bg-rose-50/80 p-3"
                    >
                      <div className="text-sm font-medium text-rose-900">
                        {gap.article}: {gap.requirement_name}
                      </div>
                      <div className="mt-1 text-xs text-rose-800/90">
                        System: {gap.ai_system_name} ({gap.ai_system_id})
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </div>
    );
  }

  // ─── Wizard View ──────────────────────────────────────────────────────────

  if (view === "wizard") {
    const setField = (key: string, val: unknown) =>
      setWizardData((d) => ({ ...d, [key]: val }));

    const systemName =
      systems.find((s) => s.id === wizardSystemId)?.name || wizardSystemId;

    if (wizardResult) {
      return (
        <div className={CH_SHELL}>
          <header className="mb-6">
            <button
              onClick={() => { setView("dashboard"); loadDashboard(); }}
              className="text-xs text-slate-600 hover:text-slate-900 mb-2 inline-block"
            >
              ← Zurück zum Dashboard
            </button>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
              Klassifizierungsergebnis – {systemName}
            </h1>
          </header>

          <div className="max-w-2xl space-y-6">
            <div className={`${CH_CARD} p-6 text-center`}>
              <div className="text-xs text-slate-600 mb-2">Risikostufe</div>
              <span
                className={cn(
                  "inline-flex rounded-full px-4 py-1.5 text-sm font-semibold",
                  RISK_BADGE[wizardResult.risk_level]
                )}
              >
                {RISK_LABEL[wizardResult.risk_level]}
              </span>
              <div className="mt-4 text-sm text-slate-900">
                {wizardResult.classification_rationale}
              </div>
              {wizardResult.classification_path !== "none" && (
                <div className="mt-3 text-xs text-slate-500">
                  Pfad: {wizardResult.classification_path} | Konfidenz:{" "}
                  {Math.round(wizardResult.confidence_score * 100)}%
                </div>
              )}
            </div>

            <button
              type="button"
              onClick={() => { setView("dashboard"); loadDashboard(); }}
              className={CH_BTN_SECONDARY}
            >
              Zurück zum Dashboard
            </button>
          </div>
        </div>
      );
    }

    return (
      <div className={CH_SHELL}>
        <header className="mb-6">
          <button
            onClick={() => setView("dashboard")}
            className="text-xs text-slate-600 hover:text-slate-900 mb-2 inline-block"
          >
            ← Zurück zum Dashboard
          </button>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
            Klassifizierungs-Assistent – {systemName}
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Schritt {wizardStep} von 5: {STEP_TITLES[wizardStep]}
          </p>
        </header>

        {/* Steps indicator */}
        <div className="mb-6 flex gap-2">
          {([1, 2, 3, 4, 5] as WizardStep[]).map((s) => (
            <div
              key={s}
              className={cn(
                "h-1.5 flex-1 rounded-full",
                s <= wizardStep ? "bg-emerald-500" : "bg-slate-200"
              )}
            />
          ))}
        </div>

        <div className="max-w-2xl space-y-4 rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm shadow-slate-200/40">
          {wizardStep === 1 && (
            <>
              <h3 className="text-sm font-semibold text-slate-900 mb-3">
                Prüfung auf verbotene Praktiken (Art. 5)
              </h3>
              {[
                { key: "involves_social_scoring", label: "Social Scoring (Sozialkreditsystem)" },
                { key: "involves_subliminal_manipulation", label: "Unterschwellige Manipulation" },
                { key: "exploits_vulnerabilities", label: "Ausnutzung von Schwachstellen (Alter, Behinderung)" },
                { key: "involves_realtime_biometric_public", label: "Biometrische Echtzeit-Fernidentifizierung in öffentlichen Räumen" },
              ].map(({ key, label }) => (
                <label key={key} className="flex items-center gap-3 text-sm text-slate-900">
                  <input
                    type="checkbox"
                    checked={!!wizardData[key]}
                    onChange={(e) => setField(key, e.target.checked)}
                    className="rounded border-slate-200 bg-slate-50"
                  />
                  {label}
                </label>
              ))}
            </>
          )}

          {wizardStep === 2 && (
            <>
              <h3 className="text-sm font-semibold text-slate-900 mb-3">
                Anhang I – Sicherheitskomponente unter EU-Harmonisierungsrecht
              </h3>
              {[
                { key: "is_product_or_safety_component", label: "Ist Produkt oder Sicherheitskomponente eines Produkts" },
                { key: "covered_by_eu_harmonisation_legislation", label: "Fällt unter EU-Harmonisierungsrecht" },
                { key: "requires_third_party_conformity", label: "Drittanbieter-Konformitätsbewertung erforderlich" },
              ].map(({ key, label }) => (
                <label key={key} className="flex items-center gap-3 text-sm text-slate-900">
                  <input
                    type="checkbox"
                    checked={!!wizardData[key]}
                    onChange={(e) => setField(key, e.target.checked)}
                    className="rounded border-slate-200 bg-slate-50"
                  />
                  {label}
                </label>
              ))}
              <div>
                <label className="block text-xs text-slate-600 mb-1">
                  Gesetzesreferenz (optional)
                </label>
                <input
                  type="text"
                  value={(wizardData.legislation_reference as string) || ""}
                  onChange={(e) => setField("legislation_reference", e.target.value || null)}
                  placeholder="z.B. Machinery Regulation 2023/1230"
                  className="w-full rounded border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-900 placeholder:text-slate-600"
                />
              </div>
            </>
          )}

          {wizardStep === 3 && (
            <>
              <h3 className="text-sm font-semibold text-slate-900 mb-3">
                Anhang III – Anwendungsbereich
              </h3>
              <div>
                <label className="block text-xs text-slate-600 mb-1">
                  Einsatzbereich
                </label>
                <select
                  value={(wizardData.use_case_domain as string) || ""}
                  onChange={(e) => setField("use_case_domain", e.target.value || null)}
                  className="w-full rounded border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-900"
                >
                  <option value="">– Keiner der aufgeführten Bereiche –</option>
                  <option value="biometrics">Biometrie</option>
                  <option value="critical_infra">Kritische Infrastruktur</option>
                  <option value="education">Bildung</option>
                  <option value="employment">Beschäftigung</option>
                  <option value="essential_services">Grundlegende Dienste</option>
                  <option value="law_enforcement">Strafverfolgung</option>
                  <option value="migration">Migration</option>
                  <option value="justice">Justiz</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-600 mb-1">
                  Spezifischer Anwendungsfall (optional)
                </label>
                <input
                  type="text"
                  value={(wizardData.specific_use_case as string) || ""}
                  onChange={(e) => setField("specific_use_case", e.target.value || null)}
                  className="w-full rounded border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-900"
                />
              </div>
            </>
          )}

          {wizardStep === 4 && (
            <>
              <h3 className="text-sm font-semibold text-slate-900 mb-3">
                Art. 6(3) – Ausnahmen von der Hochrisiko-Einstufung
              </h3>
              {[
                { key: "is_narrow_procedural_task", label: "Enge verfahrensbezogene Aufgabe" },
                { key: "improves_prior_human_activity", label: "Verbessert zuvor abgeschlossene menschliche Tätigkeit" },
                { key: "detects_patterns_without_replacing_human", label: "Erkennt Muster ohne menschliche Bewertung zu ersetzen" },
                { key: "is_preparatory_task_only", label: "Rein vorbereitende Aufgabe" },
              ].map(({ key, label }) => (
                <label key={key} className="flex items-center gap-3 text-sm text-slate-900">
                  <input
                    type="checkbox"
                    checked={!!wizardData[key]}
                    onChange={(e) => setField(key, e.target.checked)}
                    className="rounded border-slate-200 bg-slate-50"
                  />
                  {label}
                </label>
              ))}
              <div className="border-t border-slate-200 pt-3 mt-3">
                <label className="flex items-center gap-3 text-sm font-medium text-rose-800">
                  <input
                    type="checkbox"
                    checked={!!wizardData.profiles_natural_persons}
                    onChange={(e) => setField("profiles_natural_persons", e.target.checked)}
                    className="rounded border-slate-200 bg-slate-50"
                  />
                  Profiliert natürliche Personen (Ausnahme entfällt!)
                </label>
              </div>
            </>
          )}

          {wizardStep === 5 && (
            <>
              <h3 className="text-sm font-semibold text-slate-900 mb-3">
                Transparenzpflichten
              </h3>
              {[
                { key: "is_chatbot_or_conversational", label: "Chatbot / Konversations-KI" },
                { key: "generates_deepfakes", label: "Erzeugt Deepfakes" },
                { key: "involves_emotion_recognition", label: "Emotionserkennung" },
              ].map(({ key, label }) => (
                <label key={key} className="flex items-center gap-3 text-sm text-slate-900">
                  <input
                    type="checkbox"
                    checked={!!wizardData[key]}
                    onChange={(e) => setField(key, e.target.checked)}
                    className="rounded border-slate-200 bg-slate-50"
                  />
                  {label}
                </label>
              ))}
            </>
          )}

          {/* Nav buttons */}
          <div className="flex justify-between pt-4 border-t border-slate-200">
            <button
              onClick={() => setWizardStep((s) => Math.max(1, s - 1) as WizardStep)}
              disabled={wizardStep === 1}
              className="rounded border border-slate-200 px-3 py-1.5 text-xs text-slate-900 hover:bg-slate-100 disabled:opacity-40"
            >
              Zurück
            </button>
            {wizardStep < 5 ? (
              <button
                type="button"
                onClick={() => setWizardStep((s) => Math.min(5, s + 1) as WizardStep)}
                className={`${CH_BTN_SECONDARY} px-3 py-1.5 text-xs`}
              >
                Weiter
              </button>
            ) : (
              <button
                type="button"
                onClick={() => void submitClassification()}
                className={`${CH_BTN_PRIMARY} px-4 py-1.5 text-xs`}
              >
                Klassifizierung abschließen
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  // ─── Gap Analysis View ────────────────────────────────────────────────────

  if (view === "gap") {
    const systemName =
      systems.find((s) => s.id === gapSystemId)?.name || gapSystemId;
    const sr = dashboard?.systems.find((s) => s.ai_system_id === gapSystemId);

    return (
      <div className={CH_SHELL}>
        <header className="mb-6">
          <button
            onClick={() => { setView("dashboard"); loadDashboard(); }}
            className="text-xs text-slate-600 hover:text-slate-900 mb-2 inline-block"
          >
            ← Zurück zum Dashboard
          </button>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
            Lückenanalyse – {systemName}
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Compliance-Status der einzelnen Anforderungen (Art. 9–49) für dieses System.
          </p>
        </header>

        {sr && (
          <div className="mb-6 flex items-center gap-6">
            <CircularProgress value={sr.readiness_score} size={90} />
            <div>
              <div className="text-sm text-slate-600">Gesamtbereitschaft</div>
              <div className="text-2xl font-semibold">
                {Math.round(sr.readiness_score * 100)}%
              </div>
              <div className="text-xs text-slate-500 mt-1">
                {sr.completed} abgeschlossen, {sr.in_progress} in Bearbeitung,{" "}
                {sr.not_started} offen
              </div>
            </div>
          </div>
        )}

        <section className={`${CH_CARD} p-5`}>
          <h2 className="text-sm font-semibold text-slate-900">
            NIS2 / KRITIS KPIs
          </h2>
          <p className="mt-1 text-xs text-slate-500">
            Operative Kennzahlen (0–100 %) mit optionaler Evidenz-Referenz. Empfohlene
            Ziele aus dem High-Risk-Szenario-Profil, sofern das System als High-Risk
            eingeordnet ist.
          </p>
          {nis2Kpis?.recommended?.scenario_label && (
            <p className="mt-2 text-xs font-medium text-indigo-800">
              Szenario-Mapping: {nis2Kpis.recommended.scenario_label}
            </p>
          )}
          <div className="mt-4 space-y-5">
            {(
              [
                "INCIDENT_RESPONSE_MATURITY",
                "SUPPLIER_RISK_COVERAGE",
                "OT_IT_SEGREGATION",
              ] as const
            ).map((kpiType) => {
              const recPct = nis2RecommendedPercent(kpiType, nis2Kpis?.recommended ?? null);
              const draft = nis2Draft[kpiType];
              return (
                <div
                  key={kpiType}
                  className="border-t border-slate-200/80 pt-4 first:border-t-0 first:pt-0"
                >
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <span className="text-sm font-medium text-slate-900">
                      {NIS2_KPI_LABEL[kpiType]}
                    </span>
                    {recPct != null && (
                        <span className="text-xs text-slate-500">
                        Empfehlung:{" "}
                        <span className="font-medium text-emerald-700">{recPct}%</span>
                      </span>
                    )}
                  </div>
                  <div className="mt-2 flex items-center gap-3">
                    <input
                      type="range"
                      min={0}
                      max={100}
                      value={draft.value}
                      onChange={(e) =>
                        setNis2Draft((prev) => ({
                          ...prev,
                          [kpiType]: { ...prev[kpiType], value: Number(e.target.value) },
                        }))
                      }
                      className="flex-1 accent-emerald-500"
                    />
                    <span className="w-10 text-right text-sm tabular-nums text-slate-900">
                      {draft.value}%
                    </span>
                  </div>
                  {recPct != null && (
                    <div className="mt-1 h-1.5 w-full rounded-full bg-slate-200">
                      <div
                        className="h-full rounded-full bg-emerald-500/40"
                        style={{ width: `${recPct}%` }}
                      />
                    </div>
                  )}
                  <label className="mt-2 block text-xs text-slate-500">
                    Evidenz (optional, z. B. NormEvidence-IDs)
                    <input
                      type="text"
                      value={draft.evidence}
                      onChange={(e) =>
                        setNis2Draft((prev) => ({
                          ...prev,
                          [kpiType]: { ...prev[kpiType], evidence: e.target.value },
                        }))
                      }
                      className="mt-1 w-full rounded border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
                    />
                  </label>
                  <button
                    type="button"
                    onClick={() => void saveNis2Kpi(kpiType)}
                    disabled={nis2Saving === kpiType}
                    className={`${CH_BTN_SECONDARY} mt-2 px-3 py-1 text-xs disabled:opacity-50`}
                  >
                    {nis2Saving === kpiType ? "Speichern…" : "Speichern"}
                  </button>
                </div>
              );
            })}
          </div>
        </section>

        {gapStatuses.length === 0 ? (
          <div className={`${CH_CARD} p-8 text-center text-sm text-slate-500`}>
            Keine Anforderungen für dieses System vorhanden.
            Bitte zuerst eine Klassifizierung durchführen.
          </div>
        ) : (
          <div className="space-y-3">
            {gapStatuses.map((entry) => {
              const req = requirements.find((r) => r.id === entry.requirement_id);
              return (
                <div
                  key={entry.requirement_id}
                  className={`${CH_CARD} p-4`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium text-slate-900">
                        {req?.article}: {req?.name || entry.requirement_id}
                      </div>
                      <div className="text-xs text-slate-600 mt-1">
                        {req?.description}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <select
                        value={entry.status}
                        onChange={(e) =>
                          updateStatus(entry.requirement_id, e.target.value)
                        }
                        className="rounded border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
                      >
                        <option value="not_started">Nicht begonnen</option>
                        <option value="in_progress">In Bearbeitung</option>
                        <option value="completed">Abgeschlossen</option>
                        <option value="not_applicable">N/A</option>
                      </select>
                      <span
                        className={cn(
                          "inline-flex rounded-full px-2 py-0.5 text-xs font-medium",
                          STATUS_BADGE[entry.status]
                        )}
                      >
                        {STATUS_LABEL[entry.status]}
                      </span>
                    </div>
                  </div>
                  {entry.evidence_notes && (
                    <div className="mt-2 text-xs text-slate-500 bg-slate-200/50 rounded p-2">
                      {entry.evidence_notes}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  return null;
}
