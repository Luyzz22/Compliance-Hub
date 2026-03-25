"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import type { TenantSetupStatus } from "@/lib/api";
import { CH_BTN_PRIMARY, CH_BTN_SECONDARY, CH_CARD, CH_SECTION_LABEL } from "@/lib/boardLayout";

type SetupStepKey =
  | "INVENTORY"
  | "CLASSIFICATION"
  | "NIS2_KPIS"
  | "POLICIES"
  | "ACTIONS"
  | "EVIDENCE"
  | "READINESS";

type OnboardingPersona = "ciso" | "governance" | "owner";

const STORAGE_KEY = "compliancehub_guided_setup_persona";

const DEFAULT_ORDER: SetupStepKey[] = [
  "INVENTORY",
  "CLASSIFICATION",
  "NIS2_KPIS",
  "POLICIES",
  "ACTIONS",
  "EVIDENCE",
  "READINESS",
];

const PERSONA_ORDERS: Record<OnboardingPersona, SetupStepKey[]> = {
  ciso: [
    "INVENTORY",
    "NIS2_KPIS",
    "CLASSIFICATION",
    "POLICIES",
    "ACTIONS",
    "EVIDENCE",
    "READINESS",
  ],
  governance: [
    "INVENTORY",
    "CLASSIFICATION",
    "READINESS",
    "POLICIES",
    "NIS2_KPIS",
    "ACTIONS",
    "EVIDENCE",
  ],
  owner: [
    "INVENTORY",
    "CLASSIFICATION",
    "POLICIES",
    "ACTIONS",
    "NIS2_KPIS",
    "EVIDENCE",
    "READINESS",
  ],
};

const STEP_COPY: Record<SetupStepKey, { title: string; description: string; href: string }> = {
  INVENTORY: {
    title: "KI-Inventar anlegen",
    description:
      "Mindestens ein KI-System importieren oder anlegen, damit Register, KPIs und Nachweise einen Anker haben.",
    href: "/tenant/ai-systems",
  },
  CLASSIFICATION: {
    title: "High-Risk-Klassifikation",
    description:
      "EU-AI-Act-Risikoniveau und Anhang-III-Pfad je System festhalten – Grundlage für Pflichten und Board-Readiness.",
    href: "/tenant/eu-ai-act",
  },
  NIS2_KPIS: {
    title: "NIS2 / KRITIS-KPIs",
    description:
      "Für High-Risk-Systeme initiale Kennzahlen (Incident-Reife, Supplier, OT/IT) pflegen – Vorbereitung NIS2/KRITIS-Dialog.",
    href: "/tenant/ai-systems",
  },
  POLICIES: {
    title: "Kern-Policies",
    description:
      "Governance-Policies im Mandanten sichtbar und gepflegt – inkl. NIS2-/AI-Act-Bezug im Policies-Modul.",
    href: "/tenant/policies",
  },
  ACTIONS: {
    title: "Maßnahmen (Actions)",
    description:
      "Erste Governance-Maßnahmen zu Lücken oder regulatorischen Anforderungen anlegen und verfolgen.",
    href: "/board/eu-ai-act-readiness",
  },
  EVIDENCE: {
    title: "Evidenzen",
    description:
      "Nachweise (DPIA, Runbook, Policy) hochladen und mit System, Maßnahme oder Audit-Record verknüpfen.",
    href: "/tenant/ai-systems",
  },
  READINESS: {
    title: "Readiness-Baseline",
    description:
      "EU-AI-Act-Readiness einmal bewerten und Compliance-Status über reine Lückenlisten hinaus pflegen.",
    href: "/board/eu-ai-act-readiness",
  },
};

function stepDone(key: SetupStepKey, s: TenantSetupStatus): boolean {
  switch (key) {
    case "INVENTORY":
      return s.ai_inventory_completed;
    case "CLASSIFICATION":
      return s.classification_completed;
    case "NIS2_KPIS":
      return s.nis2_kpis_seeded;
    case "POLICIES":
      return s.policies_published;
    case "ACTIONS":
      return s.actions_defined;
    case "EVIDENCE":
      return s.evidence_attached;
    case "READINESS":
      return s.eu_ai_act_readiness_baseline_created;
    default:
      return false;
  }
}

function readStoredPersona(): OnboardingPersona | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (raw === "ciso" || raw === "governance" || raw === "owner") return raw;
  return null;
}

export interface GuidedSetupWizardProps {
  initialStatus: TenantSetupStatus;
  /** True wenn GET setup-status fehlgeschlagen ist (Fallback-Werte aktiv). */
  loadFailed?: boolean;
}

export function GuidedSetupWizard({ initialStatus, loadFailed = false }: GuidedSetupWizardProps) {
  const [persona, setPersona] = useState<OnboardingPersona | null>(null);

  useEffect(() => {
    const stored = readStoredPersona();
    if (stored) {
      // Client-only Rehydration aus localStorage (SSR liefert Default „governance“).
      // eslint-disable-next-line react-hooks/set-state-in-effect -- bewusst einmalig nach Mount
      setPersona(stored);
    }
  }, []);

  const order = useMemo(() => {
    if (!persona) return DEFAULT_ORDER;
    return PERSONA_ORDERS[persona];
  }, [persona]);

  const onPersonaChange = (value: OnboardingPersona) => {
    setPersona(value);
    try {
      window.localStorage.setItem(STORAGE_KEY, value);
    } catch {
      /* ignore quota / private mode */
    }
  };

  const total = initialStatus.total_steps;
  const doneCount = initialStatus.completed_steps;
  const pct = total > 0 ? Math.round((doneCount / total) * 100) : 0;

  const orderedSteps = order.map((key) => {
    const meta = STEP_COPY[key];
    return {
      key,
      title: meta.title,
      description: meta.description,
      href: meta.href,
      done: stepDone(key, initialStatus),
    };
  });

  const firstOpenIdx = orderedSteps.findIndex((x) => !x.done);

  return (
    <section aria-label="Guided Setup EU AI Act und NIS2" className={CH_CARD}>
      {loadFailed && (
        <p className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
          Setup-Status konnte nicht von der API geladen werden. Anzeige mit Platzhalterwerten –
          bitte API-Basis-URL und Mandanten-Header prüfen.
        </p>
      )}
      <div className="flex flex-col gap-4 border-b border-[var(--sbs-border)] pb-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className={CH_SECTION_LABEL}>Guided Setup</p>
          <h2 className="mt-1 text-lg font-bold text-[var(--sbs-text-primary)]">
            Setup-Assistent EU AI Act &amp; NIS2
          </h2>
          <p className="mt-2 max-w-3xl text-sm text-[var(--sbs-text-secondary)]">
            Geführte Checkliste bis zum Minimum Viable Compliance: Inventar, Klassifikation, KPIs,
            Policies, Maßnahmen, Evidenzen und erste Readiness-Baseline – abgeleitet aus echten
            Mandantendaten, ohne manuelles Abhaken.
          </p>
        </div>
        <div className="flex shrink-0 flex-col gap-2 sm:items-end">
          <label className="text-xs font-semibold text-[var(--sbs-text-secondary)]" htmlFor="guided-setup-persona">
            Onboarding-Perspektive
          </label>
          <select
            id="guided-setup-persona"
            className="rounded-lg border border-[var(--sbs-border)] bg-white px-3 py-2 text-sm text-slate-900 shadow-sm"
            value={persona ?? "governance"}
            onChange={(e) => onPersonaChange(e.target.value as OnboardingPersona)}
          >
            <option value="ciso">CISO / Security</option>
            <option value="governance">AI-Governance / Legal / DSB</option>
            <option value="owner">Fachbereich / System-Owner</option>
          </select>
          <p className="max-w-xs text-[11px] text-[var(--sbs-text-muted)]">
            Nur Anzeige: Reihenfolge und Hervorhebung passen sich leicht an (lokal gespeichert).
          </p>
        </div>
      </div>

      <div className="mt-4">
        <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
          <span className="font-semibold text-[var(--sbs-text-primary)]">
            {doneCount} von {total} Schritten abgeschlossen
          </span>
          <span className="tabular-nums text-[var(--sbs-text-secondary)]">{pct}%</span>
        </div>
        <div
          className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-200"
          role="progressbar"
          aria-valuenow={doneCount}
          aria-valuemin={0}
          aria-valuemax={total}
          aria-label="Guided-Setup-Fortschritt"
        >
          <div
            className="h-full rounded-full bg-emerald-600 transition-[width] duration-300"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      <ol className="mt-6 space-y-3">
        {orderedSteps.map((step, idx) => {
          const stateLabel = step.done
            ? "Erledigt"
            : idx === firstOpenIdx
              ? "In Arbeit"
              : "Offen";
          const ring =
            !step.done && idx === firstOpenIdx
              ? "ring-2 ring-amber-400/80 ring-offset-2 ring-offset-white"
              : "";

          return (
            <li
              key={step.key}
              className={`rounded-xl border border-[var(--sbs-border)] bg-slate-50/80 p-4 ${ring}`}
            >
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-bold text-slate-500">Schritt {idx + 1}</span>
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${
                        step.done
                          ? "bg-emerald-100 text-emerald-900"
                          : idx === firstOpenIdx
                            ? "bg-amber-100 text-amber-950"
                            : "bg-slate-200 text-slate-700"
                      }`}
                    >
                      {stateLabel}
                    </span>
                  </div>
                  <h3 className="mt-1 text-sm font-bold text-[var(--sbs-text-primary)]">
                    {step.title}
                  </h3>
                  <p className="mt-1 max-w-3xl text-sm text-[var(--sbs-text-secondary)]">
                    {step.description}
                  </p>
                  {step.key === "CLASSIFICATION" && !step.done && initialStatus.ai_inventory_completed && (
                    <p className="mt-1 text-xs text-[var(--sbs-text-muted)]">
                      Klassifikationsabdeckung:{" "}
                      {Math.round(initialStatus.classification_coverage_ratio * 100)}% der Systeme
                    </p>
                  )}
                </div>
                <Link
                  href={step.href}
                  className={step.done ? `${CH_BTN_SECONDARY} shrink-0 text-xs` : `${CH_BTN_PRIMARY} shrink-0 text-xs`}
                >
                  Jetzt erledigen
                </Link>
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
