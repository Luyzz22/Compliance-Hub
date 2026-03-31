"use client";

import Link from "next/link";
import React, { useCallback, useEffect, useMemo, useState } from "react";

import {
  createAiComplianceBoardReport,
  createTenantAiSystem,
  fetchCrossRegulationSummary,
  fetchTenantAiGovernanceSetup,
  fetchTenantAiSystemKpis,
  fetchTenantAISystems,
  logDemoFeatureUsed,
  postCrossRegulationLlmGapAssistant,
  postTenantAiSystemKpi,
  putTenantAiGovernanceSetup,
  type AISystem,
  type CrossRegFrameworkSummaryDto,
  type CrossRegLlmGapSuggestionDto,
  type TenantAiGovernanceSetupDto,
} from "@/lib/api";
import { useWorkspaceMode } from "@/hooks/useWorkspaceMode";
import {
  CH_BTN_PRIMARY,
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_SECTION_LABEL,
  CH_SHELL,
} from "@/lib/boardLayout";
import {
  featureAiComplianceBoardReport,
  featureAiKpiKri,
  featureCrossRegulationDashboard,
  featureCrossRegulationLlmAssist,
} from "@/lib/config";

const STEP_LABELS = [
  "Kontext & Rollen",
  "Framework-Setup",
  "KI-Inventar",
  "KPI-Basis",
  "Cross-Regulation",
  "Board-Report",
] as const;

const SCOPE_OPTIONS: { id: string; label: string }[] = [
  { id: "eu_ai_act_high_risk", label: "EU AI Act (High-Risk)" },
  { id: "gpai", label: "GPAI / Foundation Models" },
  { id: "nis2", label: "NIS2 / KRITIS" },
  { id: "iso_42001", label: "ISO 42001 (AIMS)" },
  { id: "iso_27001", label: "ISO 27001" },
  { id: "dsgvo", label: "DSGVO" },
];

const FRAMEWORK_OPTIONS: { key: string; title: string; hint: string }[] = [
  {
    key: "eu_ai_act",
    title: "EU AI Act",
    hint: "High-Risk-Pflichten, Logging, Risikomanagement, menschliche Aufsicht.",
  },
  {
    key: "iso_42001",
    title: "ISO/IEC 42001",
    hint: "AI-Managementsystem (AIMS) und Lebenszyklus.",
  },
  {
    key: "iso_27001",
    title: "ISO/IEC 27001",
    hint: "ISMS-Controls, die KI-Betrieb und Daten absichern.",
  },
  {
    key: "iso_27701",
    title: "ISO/IEC 27701",
    hint: "Privacy Information Management (Erweiterung von ISO 27001).",
  },
  { key: "nis2", title: "NIS2", hint: "Operative Cyber-Resilienz und Meldepfade." },
  { key: "dsgvo", title: "DSGVO", hint: "Datenschutz, DPIA-Bezug zu KI-Risiko." },
];

const ROLE_FIELDS: { key: string; label: string }[] = [
  { key: "board", label: "Board / Geschäftsführung" },
  { key: "ciso", label: "CISO / Security Lead" },
  { key: "ai_governance_lead", label: "AI Governance Lead / AIMS Owner" },
  { key: "dpo", label: "Datenschutzbeauftragte/r (DSB)" },
  { key: "advisor", label: "Berater / Kanzlei (optional)" },
];

const WIZARD_KPI_KEYS = [
  "incident_rate_ai",
  "jailbreak_success_rate",
  "pii_leakage_rate",
  "drift_indicator",
] as const;

function emptySetup(tenantId: string): TenantAiGovernanceSetupDto {
  return {
    tenant_id: tenantId,
    tenant_kind: null,
    compliance_scopes: [],
    governance_roles: {},
    active_frameworks: [],
    steps_marked_complete: [],
    flags: {},
    progress_steps: [],
  };
}

function initialStepFromProgress(progress: number[]): number {
  for (let s = 1; s <= 6; s += 1) {
    if (!progress.includes(s)) return s - 1;
  }
  return 6;
}

function systemRiskLevel(s: AISystem): string {
  return (s.risk_level ?? s.risklevel ?? "").toString();
}

function systemCriticality(s: AISystem): string {
  return (s.criticality ?? "").toString();
}

function periodBounds(freq: "monthly" | "quarterly"): { start: string; end: string } {
  const start = new Date();
  start.setUTCDate(1);
  start.setUTCHours(0, 0, 0, 0);
  const end = new Date(start);
  if (freq === "monthly") {
    end.setUTCMonth(end.getUTCMonth() + 1);
  } else {
    end.setUTCMonth(end.getUTCMonth() + 3);
  }
  end.setUTCSeconds(end.getUTCSeconds() - 1);
  return { start: start.toISOString(), end: end.toISOString() };
}

export interface AiGovernanceSetupWizardClientProps {
  tenantId: string;
  initialSetup: TenantAiGovernanceSetupDto | null;
}

export function AiGovernanceSetupWizardClient({
  tenantId,
  initialSetup,
}: AiGovernanceSetupWizardClientProps) {
  const { mutationsBlocked, isDemoTenant } = useWorkspaceMode(tenantId);

  const [setup, setSetup] = useState<TenantAiGovernanceSetupDto>(
    () => initialSetup ?? emptySetup(tenantId),
  );
  const [step, setStep] = useState(() =>
    initialSetup ? initialStepFromProgress(initialSetup.progress_steps) : 0,
  );
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [tenantKind, setTenantKind] = useState<"enterprise" | "advisor" | "">(
    () => (initialSetup?.tenant_kind as "enterprise" | "advisor" | "") ?? "",
  );
  const [scopes, setScopes] = useState<Set<string>>(
    () => new Set(initialSetup?.compliance_scopes ?? []),
  );
  const [roles, setRoles] = useState<Record<string, string>>(() => ({
    ...(initialSetup?.governance_roles ?? {}),
  }));
  const [frameworks, setFrameworks] = useState<Set<string>>(
    () => new Set(initialSetup?.active_frameworks ?? []),
  );

  const [draftName, setDraftName] = useState("");
  const [draftDesc, setDraftDesc] = useState("");
  const [draftUseCase, setDraftUseCase] = useState("");
  const [draftDomain, setDraftDomain] = useState("");
  const [draftRiskBand, setDraftRiskBand] = useState<"low" | "limited" | "high">("limited");
  const [draftEuHigh, setDraftEuHigh] = useState(false);
  const [draftNis2, setDraftNis2] = useState(false);
  const [wizardSystemIds, setWizardSystemIds] = useState<string[]>([]);
  const [systemsAddedCount, setSystemsAddedCount] = useState(0);

  const [kpiTargets, setKpiTargets] = useState<AISystem[]>([]);
  const [kpiFreq, setKpiFreq] = useState<Record<string, "monthly" | "quarterly">>({});
  const [kpiBaseline, setKpiBaseline] = useState<Record<string, Record<string, string>>>({});

  const [previewSummary, setPreviewSummary] = useState<CrossRegFrameworkSummaryDto[] | null>(null);
  const [gapSuggestions, setGapSuggestions] = useState<CrossRegLlmGapSuggestionDto[]>([]);
  const [gapBusy, setGapBusy] = useState(false);

  const [lastReportId, setLastReportId] = useState<string | null>(null);

  useEffect(() => {
    if (!isDemoTenant) return;
    void logDemoFeatureUsed(tenantId, "ai_governance_setup_wizard").catch(() => {});
  }, [isDemoTenant, tenantId]);

  useEffect(() => {
    if (initialSetup) return;
    let cancelled = false;
    void (async () => {
      try {
        const s = await fetchTenantAiGovernanceSetup(tenantId);
        if (cancelled) return;
        setSetup(s);
        setTenantKind((s.tenant_kind as "enterprise" | "advisor" | "") ?? "");
        setScopes(new Set(s.compliance_scopes ?? []));
        setRoles({ ...s.governance_roles });
        setFrameworks(new Set(s.active_frameworks ?? []));
        setStep(initialStepFromProgress(s.progress_steps));
      } catch {
        /* Defaults bleiben */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [initialSetup, tenantId]);

  const persist = useCallback(
    async (body: Parameters<typeof putTenantAiGovernanceSetup>[1]) => {
      if (mutationsBlocked) {
        setErr("Im Demo-Mandanten sind keine Speicherungen möglich (read-only).");
        return;
      }
      setBusy(true);
      setErr(null);
      try {
        const next = await putTenantAiGovernanceSetup(tenantId, body);
        setSetup(next);
        return next;
      } catch (e) {
        setErr(e instanceof Error ? e.message : "Speichern fehlgeschlagen");
        throw e;
      } finally {
        setBusy(false);
      }
    },
    [tenantId, mutationsBlocked],
  );

  const toggleScope = (id: string) => {
    setScopes((prev) => {
      const n = new Set(prev);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  };

  const toggleFramework = (key: string) => {
    setFrameworks((prev) => {
      const n = new Set(prev);
      if (n.has(key)) n.delete(key);
      else n.add(key);
      return n;
    });
  };

  const stepDone = useCallback(
    (n: number) => setup.progress_steps.includes(n),
    [setup.progress_steps],
  );

  const goNext = async () => {
    const sn = step + 1;
    if (sn <= 6 && !mutationsBlocked) {
      await persist({ mark_steps_complete: [sn] });
    }
    setStep((s) => Math.min(6, s + 1));
  };

  const goSkip = async () => {
    const sn = step + 1;
    if (sn <= 6 && !mutationsBlocked) {
      await persist({ mark_steps_complete: [sn] });
    }
    setStep((s) => Math.min(6, s + 1));
  };

  const saveStep1 = async () => {
    if (!tenantKind) {
      setErr("Bitte wählen Sie aus, ob Sie Mittelstand oder Beratung sind.");
      return;
    }
    await persist({
      tenant_kind: tenantKind,
      compliance_scopes: Array.from(scopes),
      governance_roles: roles,
      mark_steps_complete: [1],
    });
    setStep(1);
  };

  const saveStep2 = async () => {
    await persist({
      active_frameworks: Array.from(frameworks),
      mark_steps_complete: [2],
    });
    setStep(2);
  };

  const addSystemToRegister = async () => {
    if (mutationsBlocked) {
      setErr("Im Demo-Mandanten können keine neuen KI-Systeme angelegt werden.");
      return;
    }
    if (!draftName.trim()) {
      setErr("System-Name ist erforderlich.");
      return;
    }
    setErr(null);
    const id = `ags-${crypto.randomUUID().replace(/-/g, "").slice(0, 20)}`;
    let risk_level: string;
    let ai_act_category: string;
    let gdpr_dpia_required: boolean;
    if (draftEuHigh) {
      risk_level = "high";
      ai_act_category = "high_risk";
      gdpr_dpia_required = true;
    } else if (draftRiskBand === "high") {
      risk_level = "high";
      ai_act_category = "high_risk";
      gdpr_dpia_required = true;
    } else if (draftRiskBand === "limited") {
      risk_level = "limited";
      ai_act_category = "limited_risk";
      gdpr_dpia_required = false;
    } else {
      risk_level = "low";
      ai_act_category = "minimal_risk";
      gdpr_dpia_required = false;
    }
    const criticality = draftNis2 ? "very_high" : "medium";
    const description = [draftDesc.trim(), draftUseCase.trim()].filter(Boolean).join("\n\n") || "—";
    setBusy(true);
    try {
      await createTenantAiSystem(tenantId, {
        id,
        name: draftName.trim(),
        description,
        business_unit: draftDomain.trim() || "Allgemein",
        risk_level,
        ai_act_category,
        gdpr_dpia_required,
        criticality,
        data_sensitivity: "internal",
      });
      setWizardSystemIds((prev) => [...prev, id]);
      setSystemsAddedCount((c) => c + 1);
      setDraftName("");
      setDraftDesc("");
      setDraftUseCase("");
      setDraftDomain("");
      setDraftRiskBand("limited");
      setDraftEuHigh(false);
      setDraftNis2(false);
      await persist({ mark_steps_complete: [3] });
    } catch (e) {
      setErr(e instanceof Error ? e.message : "System konnte nicht angelegt werden");
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    if (step !== 3 || !featureAiKpiKri()) return;
    let cancelled = false;
    void (async () => {
      try {
        const all = await fetchTenantAISystems(tenantId);
        if (cancelled) return;
        const filtered = all.filter(
          (s) => systemRiskLevel(s) === "high" || systemCriticality(s) === "very_high",
        );
        setKpiTargets(filtered);
        setKpiFreq((prev) => {
          const next = { ...prev };
          for (const s of filtered) {
            if (!next[s.id]) next[s.id] = "monthly";
          }
          return next;
        });
      } catch {
        /* ignore */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [step, tenantId]);

  useEffect(() => {
    if (step !== 4 || !featureCrossRegulationDashboard()) return;
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetchCrossRegulationSummary(tenantId);
        if (cancelled) return;
        let fw = res.frameworks;
        if (setup.active_frameworks?.length) {
          const pref = new Set(setup.active_frameworks);
          const sub = fw.filter((f) => pref.has(f.framework_key));
          if (sub.length) fw = sub;
        }
        setPreviewSummary(fw);
      } catch {
        setPreviewSummary(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [step, tenantId, setup.active_frameworks]);

  const saveKpis = async () => {
    if (mutationsBlocked) {
      setErr("Im Demo-Mandanten können keine KPI-Werte gespeichert werden.");
      return;
    }
    if (!featureAiKpiKri()) {
      await persist({ mark_steps_complete: [4] });
      setStep(4);
      return;
    }
    setBusy(true);
    setErr(null);
    try {
      for (const sys of kpiTargets) {
        const freq = kpiFreq[sys.id] ?? "monthly";
        const bounds = periodBounds(freq);
        const list = await fetchTenantAiSystemKpis(tenantId, sys.id);
        const byKey = new Map(list.series.map((s) => [s.definition.key, s.definition.id]));
        for (const key of WIZARD_KPI_KEYS) {
          const defId = byKey.get(key);
          if (!defId) continue;
          const raw = kpiBaseline[sys.id]?.[key]?.trim();
          const value = raw === "" || raw === undefined ? 0 : Number(raw);
          if (Number.isNaN(value)) continue;
          await postTenantAiSystemKpi(tenantId, sys.id, {
            kpi_definition_id: defId,
            period_start: bounds.start,
            period_end: bounds.end,
            value,
            source: "manual",
            comment: "AI-Governance-Setup-Wizard",
          });
        }
      }
      await persist({ mark_steps_complete: [4] });
      setStep(4);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "KPI-Speichern fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  };

  const runGapAssist = async () => {
    if (mutationsBlocked) {
      setErr("KI-Gap-Assist ist im Demo-Mandanten (read-only) deaktiviert.");
      return;
    }
    if (!featureCrossRegulationLlmAssist()) return;
    setGapBusy(true);
    setErr(null);
    try {
      const res = await postCrossRegulationLlmGapAssistant(tenantId, {
        focus_frameworks: setup.active_frameworks?.length ? setup.active_frameworks : null,
        max_suggestions: 5,
      });
      setGapSuggestions(res.suggestions.slice(0, 5));
      await persist({ flags: { gap_assist_previewed: true }, mark_steps_complete: [5] });
    } catch (e) {
      setErr(e instanceof Error ? e.message : "KI-Gap-Analyse fehlgeschlagen");
    } finally {
      setGapBusy(false);
    }
  };

  const generateBoardReport = async () => {
    if (mutationsBlocked) {
      setErr("Board-Report-Generierung ist im Demo-Mandanten (read-only) deaktiviert.");
      return;
    }
    if (!featureAiComplianceBoardReport()) return;
    setBusy(true);
    setErr(null);
    try {
      const res = await createAiComplianceBoardReport(tenantId, {
        audience_type: "board",
        focus_frameworks: setup.active_frameworks?.length ? setup.active_frameworks : null,
        language: "de",
      });
      setLastReportId(res.report_id);
      await persist({
        flags: { board_report_created: true },
        mark_steps_complete: [6],
      });
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Board-Report fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  };

  const progressLabel = useMemo(() => {
    const max = 6;
    const done = setup.progress_steps.filter((n) => n >= 1 && n <= max).length;
    return `${Math.min(done, max)} / ${max}`;
  }, [setup.progress_steps]);

  return (
    <div className={CH_SHELL} data-testid="ai-governance-setup-wizard">
      <header className="mb-8">
        <p className="text-[0.7rem] font-bold uppercase tracking-[0.14em] text-cyan-800">
          Mandanten-Workspace
        </p>
        {mutationsBlocked ? (
          <div
            className="mt-3 rounded-lg border border-amber-200 bg-amber-50/90 px-3 py-2 text-sm text-amber-950"
            role="status"
            data-testid="wizard-demo-readonly-banner"
          >
            <strong className="font-semibold">Demo (read-only):</strong> Sie können den Ablauf
            durchklicken; Speichern, neue Systeme, KPI-Posts, KI-Gap-Assist und neue Board-Reports
            sind deaktiviert.
          </div>
        ) : null}
        <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-900">
          AI Governance Setup
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-600">
          Geführte Journey für High-Risk- und kritische KI-Systeme: Rollen, Frameworks, Register,
          KPI-Basis, Cross-Regulation und erster Board-Report – board-ready in wenigen Tagen.
        </p>
        <p className="mt-2 text-xs text-slate-500">
          Mandant: <span className="font-mono font-semibold text-slate-800">{tenantId}</span> ·
          Fortschritt: {progressLabel}
        </p>
      </header>

      <nav
        className="mb-8 flex flex-wrap gap-2"
        aria-label="Wizard-Schritte"
        data-testid="wizard-stepper"
      >
        {STEP_LABELS.map((label, i) => {
          const n = i + 1;
          const active = step === i;
          const done = stepDone(n);
          return (
            <button
              key={label}
              type="button"
              onClick={() => setStep(i)}
              className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                active
                  ? "border-cyan-600 bg-cyan-50 text-cyan-950"
                  : done
                    ? "border-emerald-200 bg-emerald-50 text-emerald-900"
                    : "border-slate-200 bg-white text-slate-600 hover:border-slate-300"
              }`}
            >
              {n}. {label}
              {done ? " ✓" : ""}
            </button>
          );
        })}
        <button
          type="button"
          onClick={() => setStep(6)}
          className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
            step === 6
              ? "border-cyan-600 bg-cyan-50 text-cyan-950"
              : "border-slate-200 bg-white text-slate-600"
          }`}
        >
          Abschluss
        </button>
      </nav>

      {err ? (
        <div className="mb-6 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900">
          {err}
        </div>
      ) : null}

      {step === 0 ? (
        <section className={CH_CARD} data-testid="wizard-step-1">
          <p className={CH_SECTION_LABEL}>Schritt 1 · Kontext &amp; Rollen</p>
          <p className="mt-2 text-sm text-slate-600">
            Wer sind Sie, welche Scopes sind relevant, und wer sind die Ansprechpartner für Board,
            Security und AI Governance?
          </p>

          <div className="mt-6 space-y-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Wer sind Sie?
            </p>
            <label className="flex cursor-pointer items-center gap-2 text-sm">
              <input
                type="radio"
                name="tenant-kind"
                checked={tenantKind === "enterprise"}
                onChange={() => setTenantKind("enterprise")}
              />
              Mittelstand / Enterprise
            </label>
            <label className="flex cursor-pointer items-center gap-2 text-sm">
              <input
                type="radio"
                name="tenant-kind"
                checked={tenantKind === "advisor"}
                onChange={() => setTenantKind("advisor")}
              />
              Beratung / Kanzlei / GRC-Boutique
            </label>
          </div>

          <div className="mt-6">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Compliance-Scopes
            </p>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              {SCOPE_OPTIONS.map((o) => (
                <label key={o.id} className="flex cursor-pointer items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={scopes.has(o.id)}
                    onChange={() => toggleScope(o.id)}
                  />
                  {o.label}
                </label>
              ))}
            </div>
          </div>

          <div className="mt-6 space-y-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Schlüsselrollen (Freitext oder E-Mail)
            </p>
            <p className="text-xs text-slate-500">
              Nutzerliste aus dem IAM kann später angebunden werden; vorerst Zuordnung als Text.
            </p>
            {ROLE_FIELDS.map((r) => (
              <label key={r.key} className="block text-sm">
                <span className="text-xs font-semibold text-slate-600">{r.label}</span>
                <input
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                  value={roles[r.key] ?? ""}
                  onChange={(e) => setRoles((prev) => ({ ...prev, [r.key]: e.target.value }))}
                  placeholder="Name oder E-Mail"
                />
              </label>
            ))}
          </div>

          <div className="mt-8 flex flex-wrap gap-3">
            <button
              type="button"
              className={CH_BTN_PRIMARY}
              disabled={busy}
              onClick={() => void saveStep1()}
            >
              Speichern &amp; weiter
            </button>
            <button type="button" className={CH_BTN_SECONDARY} disabled={busy} onClick={() => void goSkip()}>
              Überspringen
            </button>
          </div>
        </section>
      ) : null}

      {step === 1 ? (
        <section className={CH_CARD} data-testid="wizard-step-2">
          <p className={CH_SECTION_LABEL}>Schritt 2 · Framework-Setup &amp; Cross-Regulation</p>
          <p className="mt-2 text-sm text-slate-600">
            Aktive Regelwerke steuern die Voreinstellung im Cross-Regulation-Dashboard und beim
            Board-Report-Generator.
          </p>
          <p className="mt-3 rounded-lg border border-amber-100 bg-amber-50/60 px-3 py-2 text-xs text-amber-950">
            Empfohlen für DACH Enterprise: EU AI Act + ISO 42001 + ISO 27001/27701 + NIS2 + DSGVO.
          </p>
          <div className="mt-4 space-y-3">
            {FRAMEWORK_OPTIONS.map((f) => (
              <label
                key={f.key}
                className="flex cursor-pointer gap-3 rounded-lg border border-slate-200 bg-slate-50/50 p-3"
              >
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={frameworks.has(f.key)}
                  onChange={() => toggleFramework(f.key)}
                />
                <div>
                  <div className="text-sm font-semibold text-slate-900">{f.title}</div>
                  <div className="text-xs text-slate-600">{f.hint}</div>
                  <div className="mt-1 font-mono text-[10px] text-slate-400">{f.key}</div>
                </div>
              </label>
            ))}
          </div>
          <div className="mt-8 flex flex-wrap gap-3">
            <button
              type="button"
              className={CH_BTN_PRIMARY}
              disabled={busy}
              onClick={() => void saveStep2()}
            >
              Speichern &amp; weiter
            </button>
            <button type="button" className={CH_BTN_SECONDARY} disabled={busy} onClick={() => void goSkip()}>
              Überspringen
            </button>
          </div>
        </section>
      ) : null}

      {step === 2 ? (
        <section className={CH_CARD} data-testid="wizard-step-3">
          <p className={CH_SECTION_LABEL}>Schritt 3 · AI-System-Inventar (High-Risk-Fokus)</p>
          <p className="mt-2 text-sm text-slate-600">
            EU AI Act High-Risk und NIS2-sensible KI-Anwendungen zuerst erfassen. Details können Sie
            später im KI-System-Modul verfeinern.
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <label className="block text-sm">
              <span className="text-xs font-semibold text-slate-600">System-Name *</span>
              <input
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                value={draftName}
                onChange={(e) => setDraftName(e.target.value)}
              />
            </label>
            <label className="block text-sm">
              <span className="text-xs font-semibold text-slate-600">Kritische Domäne / Bereich</span>
              <input
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                value={draftDomain}
                onChange={(e) => setDraftDomain(e.target.value)}
                placeholder="z. B. HR, ICS, KRITIS"
              />
            </label>
            <label className="col-span-full block text-sm">
              <span className="text-xs font-semibold text-slate-600">Beschreibung</span>
              <textarea
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                rows={2}
                value={draftDesc}
                onChange={(e) => setDraftDesc(e.target.value)}
              />
            </label>
            <label className="col-span-full block text-sm">
              <span className="text-xs font-semibold text-slate-600">Use Case</span>
              <textarea
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                rows={2}
                value={draftUseCase}
                onChange={(e) => setDraftUseCase(e.target.value)}
              />
            </label>
          </div>
          <div className="mt-4">
            <p className="text-xs font-semibold text-slate-600">Risiko (grob)</p>
            <select
              className="mt-1 w-full max-w-md rounded-lg border border-slate-200 px-3 py-2 text-sm"
              value={draftRiskBand}
              onChange={(e) => setDraftRiskBand(e.target.value as typeof draftRiskBand)}
            >
              <option value="low">Niedrig / Minimal Risk</option>
              <option value="limited">Begrenzt / Limited Risk</option>
              <option value="high">Hoch / High-Risk (ohne Checkbox)</option>
            </select>
          </div>
          <div className="mt-4 flex flex-wrap gap-4 text-sm">
            <label className="flex cursor-pointer items-center gap-2">
              <input
                type="checkbox"
                checked={draftEuHigh}
                onChange={(e) => setDraftEuHigh(e.target.checked)}
              />
              Potentiell High-Risk nach EU AI Act
            </label>
            <label className="flex cursor-pointer items-center gap-2">
              <input
                type="checkbox"
                checked={draftNis2}
                onChange={(e) => setDraftNis2(e.target.checked)}
              />
              NIS2-kritisch
            </label>
          </div>
          <div className="mt-6 flex flex-wrap gap-3">
            <button
              type="button"
              className={CH_BTN_PRIMARY}
              disabled={busy}
              onClick={() => void addSystemToRegister()}
            >
              System zum Register hinzufügen
            </button>
            <Link href="/tenant/ai-systems" className={`${CH_BTN_SECONDARY} inline-flex items-center`}>
              Details im KI-System-Modul
            </Link>
          </div>
          <p className="mt-4 text-sm text-slate-600">
            In dieser Session hinzugefügt:{" "}
            <span className="font-semibold text-slate-900">{systemsAddedCount}</span>
            {wizardSystemIds.length > 0 ? (
              <span className="ml-2 font-mono text-xs text-slate-500">
                ({wizardSystemIds.join(", ")})
              </span>
            ) : null}
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <button type="button" className={CH_BTN_PRIMARY} disabled={busy} onClick={() => void goNext()}>
              Weiter
            </button>
            <button type="button" className={CH_BTN_SECONDARY} disabled={busy} onClick={() => void goSkip()}>
              Überspringen
            </button>
          </div>
        </section>
      ) : null}

      {step === 3 ? (
        <section className={CH_CARD} data-testid="wizard-step-4">
          <p className={CH_SECTION_LABEL}>Schritt 4 · AI-KPI/KRI-Basis</p>
          <p className="mt-2 text-sm text-slate-600">
            Für High-Risk- oder NIS2-kritische Systeme: Standard-KPIs mit optionalem Baseline-Wert
            und Messfrequenz.
          </p>
          {!featureAiKpiKri() ? (
            <p className="mt-4 text-sm text-amber-800">
              AI-KPI/KRI ist in dieser Umgebung deaktiviert – Schritt kann übersprungen werden.
            </p>
          ) : kpiTargets.length === 0 ? (
            <p className="mt-4 text-sm text-slate-600">
              Keine High-Risk- oder sehr hochkritischen Systeme gefunden. Legen Sie in Schritt 3
              entsprechende Systeme an oder klassifizieren Sie bestehende Systeme.
            </p>
          ) : (
            <div className="mt-6 space-y-8">
              {kpiTargets.map((sys) => (
                <div key={sys.id} className="rounded-xl border border-slate-200 p-4">
                  <p className="text-sm font-bold text-slate-900">{sys.name}</p>
                  <p className="font-mono text-[11px] text-slate-500">{sys.id}</p>
                  <label className="mt-3 block text-xs font-semibold text-slate-600">
                    Messfrequenz
                    <select
                      className="mt-1 w-full max-w-xs rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
                      value={kpiFreq[sys.id] ?? "monthly"}
                      onChange={(e) =>
                        setKpiFreq((p) => ({
                          ...p,
                          [sys.id]: e.target.value as "monthly" | "quarterly",
                        }))
                      }
                    >
                      <option value="monthly">Monatlich</option>
                      <option value="quarterly">Quartalsweise</option>
                    </select>
                  </label>
                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    {WIZARD_KPI_KEYS.map((key) => (
                      <label key={key} className="block text-xs">
                        <span className="font-semibold text-slate-700">{key.replace(/_/g, " ")}</span>
                        <input
                          className="mt-1 w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
                          inputMode="decimal"
                          placeholder="Baseline / letzter Wert (optional, 0 wenn leer)"
                          value={kpiBaseline[sys.id]?.[key] ?? ""}
                          onChange={(e) =>
                            setKpiBaseline((p) => ({
                              ...p,
                              [sys.id]: { ...(p[sys.id] ?? {}), [key]: e.target.value },
                            }))
                          }
                        />
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
          <div className="mt-8 flex flex-wrap gap-3">
            <button
              type="button"
              className={CH_BTN_PRIMARY}
              disabled={busy}
              onClick={() => void saveKpis()}
            >
              KPIs speichern &amp; weiter
            </button>
            <button type="button" className={CH_BTN_SECONDARY} disabled={busy} onClick={() => void goSkip()}>
              Überspringen
            </button>
          </div>
        </section>
      ) : null}

      {step === 4 ? (
        <section className={CH_CARD} data-testid="wizard-step-5">
          <p className={CH_SECTION_LABEL}>Schritt 5 · Cross-Regulation &amp; KI-Gap-Assist</p>
          {!featureCrossRegulationDashboard() ? (
            <p className="mt-2 text-sm text-amber-800">
              Cross-Regulation-Dashboard ist deaktiviert.
            </p>
          ) : previewSummary && previewSummary.length > 0 ? (
            <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {previewSummary.map((f) => (
                <article key={f.framework_key} className="rounded-lg border border-slate-200 p-3">
                  <p className="text-xs font-bold uppercase text-slate-500">{f.framework_key}</p>
                  <p className="text-sm font-semibold text-slate-900">{f.name}</p>
                  <p className="mt-2 text-2xl font-bold text-cyan-800">{f.coverage_percent}%</p>
                  <p className="text-xs text-slate-600">
                    {f.gap_count} Lücken · {f.total_requirements} Pflichten
                  </p>
                </article>
              ))}
            </div>
          ) : (
            <p className="mt-2 text-sm text-slate-600">Coverage-Daten konnten nicht geladen werden.</p>
          )}

          {featureCrossRegulationLlmAssist() ? (
            <div className="mt-8">
              <button
                type="button"
                className={CH_BTN_PRIMARY}
                disabled={gapBusy}
                onClick={() => void runGapAssist()}
              >
                {gapBusy ? "Analyse läuft…" : "KI-Gap-Analyse ausführen"}
              </button>
              {gapSuggestions.length > 0 ? (
                <ul className="mt-4 space-y-3">
                  {gapSuggestions.map((s, idx) => (
                    <li
                      key={`${s.suggested_control_name}-${idx}`}
                      className="rounded-lg border border-slate-200 bg-slate-50/80 p-3 text-sm"
                    >
                      <p className="font-semibold text-slate-900">{s.suggested_control_name}</p>
                      <p className="text-xs text-slate-600">{s.rationale}</p>
                      <p className="mt-1 text-[11px] text-slate-500">
                        Priorität: {s.priority} · Frameworks: {s.frameworks.join(", ")}
                      </p>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : (
            <p className="mt-4 text-xs text-slate-500">
              KI-Gap-Assist ist in dieser Umgebung deaktiviert.
            </p>
          )}

          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/tenant/cross-regulation-dashboard" className={CH_BTN_SECONDARY}>
              Vollständiges Dashboard
            </Link>
            <button type="button" className={CH_BTN_PRIMARY} disabled={busy} onClick={() => void goNext()}>
              Weiter
            </button>
            <button type="button" className={CH_BTN_SECONDARY} disabled={busy} onClick={() => void goSkip()}>
              Überspringen
            </button>
          </div>
        </section>
      ) : null}

      {step === 5 ? (
        <section className={CH_CARD} data-testid="wizard-step-6">
          <p className={CH_SECTION_LABEL}>Schritt 6 · Board-Report-Schnellstart</p>
          <p className="mt-2 text-sm text-slate-600">
            Ihr Setup lässt sich in einem AI-Compliance-Board-Report zusammenfassen (Audience: Board,
            Frameworks aus Schritt 2).
          </p>
          {featureAiComplianceBoardReport() ? (
            <div className="mt-6 flex flex-wrap gap-3">
              <button
                type="button"
                className={CH_BTN_PRIMARY}
                disabled={busy}
                onClick={() => void generateBoardReport()}
              >
                Ersten AI-Compliance-Board-Report generieren
              </button>
              {lastReportId ? (
                <Link
                  href="/board/ai-compliance-report"
                  className={`${CH_BTN_SECONDARY} inline-flex items-center`}
                >
                  Report ansehen
                </Link>
              ) : null}
            </div>
          ) : (
            <p className="mt-4 text-sm text-amber-800">Board-Report-Feature ist deaktiviert.</p>
          )}
          <div className="mt-8 flex flex-wrap gap-3">
            <button type="button" className={CH_BTN_PRIMARY} disabled={busy} onClick={() => void goNext()}>
              Zum Abschluss
            </button>
            <button type="button" className={CH_BTN_SECONDARY} disabled={busy} onClick={() => void goSkip()}>
              Überspringen
            </button>
          </div>
        </section>
      ) : null}

      {step === 6 ? (
        <section className={CH_CARD} data-testid="wizard-finish">
          <p className={CH_SECTION_LABEL}>Abschluss</p>
          <p className="mt-2 text-sm text-slate-600">
            Diese Bausteine sind jetzt angebunden bzw. vorbereitet:
          </p>
          <ul className="mt-4 list-inside list-disc space-y-2 text-sm text-slate-800">
            <li>Governance-Rollen &amp; Scope (Tenant-Metadaten)</li>
            <li>KI-System-Register (Basis über API)</li>
            <li>Framework-Setup &amp; Regelwerksgraph (Cross-Regulation)</li>
            <li>AI-KPIs (wenn Feature aktiv und Werte gepflegt)</li>
            <li>Cross-Regulation KI-Gap-Assist (optional, LLM)</li>
            <li>Erster Board-Report (wenn generiert)</li>
          </ul>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/tenant/compliance-overview" className={CH_BTN_SECONDARY}>
              Zur Compliance-Übersicht
            </Link>
            <Link href="/tenant/ai-governance-playbook" className={CH_BTN_SECONDARY}>
              Zum Playbook
            </Link>
            <Link href="/board/kpis" className={CH_BTN_PRIMARY}>
              Board-KPIs
            </Link>
          </div>
        </section>
      ) : null}
    </div>
  );
}
