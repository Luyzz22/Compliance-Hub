import { NIS2_WIZARD_KEYS, type Nis2GovernanceMaturity, type Nis2Sector, type Nis2TriState } from "@/lib/nis2WizardModels";

export type Nis2Exposure = "hoch" | "mittel" | "niedrig";

export interface Nis2ReadinessResult {
  /** 0–100, höher = eher NIS2-/KRITIS-relevant (Indikation, keine Rechtsberatung). */
  inScopeScore: number;
  exposure: Nis2Exposure;
  /** Indikation „Kritische Organisation light“ (Marketing/Enablement, keine Behördenklassifikation). */
  criticalOrganizationLight: boolean;
  /** Empfohlene Control-Cluster-IDs für spätere profile_control_packs-Verknüpfung (Stub). */
  recommendedControlClusters: string[];
  nextSteps: string[];
}

function asTriState(v: unknown): Nis2TriState | undefined {
  if (v === "yes" || v === "no" || v === "unsure") {
    return v;
  }
  return undefined;
}

function sectorWeight(sector: unknown): number {
  const s = sector as Nis2Sector | undefined;
  const map: Partial<Record<Nis2Sector, number>> = {
    energy: 28,
    health: 26,
    transport: 22,
    digital_provider: 24,
    finance: 18,
    other: 8,
  };
  return s ? (map[s] ?? 8) : 0;
}

function bucketWeight(emp: unknown, rev: unknown): number {
  let w = 0;
  if (emp === "large" || emp === "enterprise") {
    w += 22;
  } else if (emp === "medium") {
    w += 14;
  } else if (emp === "small") {
    w += 8;
  }
  if (rev === "over_250m" || rev === "50_250m") {
    w += 18;
  } else if (rev === "under_50m") {
    w += 6;
  }
  return Math.min(40, w);
}

/**
 * Heuristische Client-Bewertung (DE: NIS2/BSIG, KRITIS-Dachgesetz).
 *
 * TODO Backend: Regelengine mit Mandanten-Branche, KRITIS-Registerabgleich, BSIG-§-Mapping,
 * Lieferketten-Tiefe, verbindliche Rechtsauskunft durch Fachstelle; keine Score-Garantie.
 */
export function computeNis2Readiness(answers: Record<string, unknown>): Nis2ReadinessResult {
  const eds = asTriState(answers[NIS2_WIZARD_KEYS.essentialDigitalServices]);
  const sup = asTriState(answers[NIS2_WIZARD_KEYS.supplierToNis2Entity]);
  const gov = answers[NIS2_WIZARD_KEYS.governanceMaturity] as Nis2GovernanceMaturity | undefined;

  let score =
    sectorWeight(answers[NIS2_WIZARD_KEYS.sector]) +
    bucketWeight(answers[NIS2_WIZARD_KEYS.employeeBucket], answers[NIS2_WIZARD_KEYS.revenueBucket]);

  if (eds === "yes") {
    score += 18;
  } else if (eds === "unsure") {
    score += 8;
  }
  if (sup === "yes") {
    score += 20;
  } else if (sup === "unsure") {
    score += 6;
  }
  if (gov === "none" || gov === "basic") {
    score += 6;
  } else if (gov === "isms_partial") {
    score += 2;
  }

  score = Math.max(0, Math.min(100, Math.round(score)));

  let exposure: Nis2Exposure = "niedrig";
  if (score >= 72) {
    exposure = "hoch";
  } else if (score >= 42) {
    exposure = "mittel";
  }

  const criticalOrganizationLight =
    exposure === "hoch" || (exposure === "mittel" && (sup === "yes" || eds === "yes"));

  const recommendedControlClusters: string[] = [];
  if (exposure === "hoch" || criticalOrganizationLight) {
    recommendedControlClusters.push("nis2_full", "supply_chain_due_diligence");
  }
  if (sup === "yes" || answers[NIS2_WIZARD_KEYS.sector] === "energy") {
    recommendedControlClusters.push("kritis_light");
  }
  if (recommendedControlClusters.length === 0) {
    recommendedControlClusters.push("nis2_baseline_readiness");
  }

  const nextSteps: string[] = [
    "Ergebnis mit Geschäftsleitung / Compliance abstimmen (persönliche Geschäftsleiterhaftung).",
    "Lieferketten- und Dienstleisterregister gegen NIS2-Pflichtige abgleichen (TODO: Backend-Abfrage).",
    "Empfohlene Maßnahmen-Cluster im Control-Center aktivieren (TODO: nis2_profiles ↔ control_packs).",
  ];

  return {
    inScopeScore: score,
    exposure,
    criticalOrganizationLight,
    recommendedControlClusters: [...new Set(recommendedControlClusters)],
    nextSteps,
  };
}
