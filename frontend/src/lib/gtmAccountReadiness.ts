/**
 * Wave 33 – grobe Produkt-/Governance-Readiness-Klassen für GTM-Brücke.
 * Regeln bewusst einfach und im Code dokumentiert; später feinjustierbar.
 */

export type GtmReadinessClass =
  | "no_footprint"
  | "early_pilot"
  | "baseline_governance"
  | "advanced_governance";

export const GTM_READINESS_CLASSES: readonly GtmReadinessClass[] = [
  "no_footprint",
  "early_pilot",
  "baseline_governance",
  "advanced_governance",
] as const;

export const GTM_READINESS_LABELS_DE: Record<GtmReadinessClass, string> = {
  no_footprint: "Kein Mandanten-Footprint (nur GTM)",
  early_pilot: "Pilot / dünn im Produkt",
  baseline_governance: "Baseline-Governance (Board/KPIs/Inventar)",
  advanced_governance: "Stärkere AI/GRC-Abdeckung",
};

/** Kompakt für Tabellen-Legenden in /admin/gtm. */
export const GTM_READINESS_SHORT_DE: Record<GtmReadinessClass, string> = {
  no_footprint: "Kein Footprint",
  early_pilot: "Pilot",
  baseline_governance: "Baseline",
  advanced_governance: "Advanced",
};

/** Signale aus FastAPI (AI-Governance-Setup + AI-System-Liste). */
export type GtmGovernanceSignalsInput = {
  ai_systems_count: number;
  /** Aus TenantAIGovernanceSetupResponse.progress_steps (1–6, DB-abgeleitet). */
  progress_steps: number[];
  active_frameworks: string[];
  /** Backend erreichbar und Antwort parsebar. */
  fetch_ok: boolean;
  /** Aus Mapping-Datei: expliziter Pilot, setzt Untergrenze early_pilot. */
  pilot_flag?: boolean;
};

function hasStep(steps: number[], n: number): boolean {
  return steps.includes(n);
}

/**
 * Klassifiziert einen **gemappten** Mandanten anhand Produkt-Signalen.
 * `no_footprint` wird hier nicht vergeben (nur für ungemappte Leads).
 *
 * Regeln (Stand Wave 33):
 * - advanced: Fortschrittsschritt 6 (Board-Report) UND mindestens 2 KI-Systeme UND ≥2 aktive Frameworks.
 * - baseline: Schritt 6 ODER (Inventar/Schritt 3 bzw. sys≥1 UND KPI-Schritt 4).
 * - early_pilot: Mandant gemappt, aber unter Baseline-Schwelle (oder Backend nicht lesbar).
 */
export function classifyMappedTenantReadiness(input: GtmGovernanceSignalsInput): GtmReadinessClass {
  const sys = input.ai_systems_count;
  const steps = input.progress_steps;
  const fw = input.active_frameworks;

  if (!input.fetch_ok) {
    return "early_pilot";
  }

  const inv = hasStep(steps, 3) || sys >= 1;
  const kpis = hasStep(steps, 4);
  const board = hasStep(steps, 6);
  const multiFramework = fw.length >= 2;

  if (board && sys >= 2 && multiFramework) {
    return "advanced_governance";
  }
  if (board || (inv && kpis)) {
    return "baseline_governance";
  }
  return "early_pilot";
}
