/**
 * NIS2 / KRITIS-DACH — Wizard-Domain (Block 3 Roadmap).
 *
 * Backend-Datenmodell (textuell, siehe Produkt-Doku):
 * - nis2_profiles: pro Mandant Ankerprofil (Sektor, Größen-Buckets, Lieferkettenrolle,
 *   zuletzt berechneter InScope-Score, empfohlene Control-Cluster-IDs).
 *   Verknüpfung zu Control-Sets: nis2_profiles.recommended_control_pack_ids[] oder Join-Tabelle
 *   profile_control_packs (profile_id, pack_id, priority) → referenziert normierte
 *   Kontrollpakete (z. B. „NIS2 Full“, „KRITIS light“, ISO 27001 Annex A Subset) ohne DDL hier.
 * - nis2_assessment_sessions: Lauf des Wizards (status, schema_version, started_at, completed_at).
 * - nis2_answers: (session_id, question_key, value JSON, updated_at) analog AI-Act-Self-Assessment.
 */

export type Nis2WizardSessionStatus = "draft" | "in_progress" | "completed";

export interface Nis2WizardSession {
  session_id: string;
  tenant_id: string;
  status: Nis2WizardSessionStatus;
  schema_version?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
}

/** Frage-Schlüssel — Abstimmung mit späterem Backend-Contract. */
export const NIS2_WIZARD_KEYS = {
  employeeBucket: "employee_bucket",
  revenueBucket: "revenue_bucket",
  sector: "sector",
  essentialDigitalServices: "essential_digital_services",
  supplierToNis2Entity: "supplier_to_nis2_entity",
  governanceMaturity: "governance_maturity",
} as const;

export type Nis2EmployeeBucket = "micro" | "small" | "medium" | "large" | "enterprise";
export type Nis2RevenueBucket = "under_50m" | "50_250m" | "over_250m" | "unknown";
export type Nis2Sector =
  | "energy"
  | "health"
  | "transport"
  | "digital_provider"
  | "finance"
  | "other";
export type Nis2TriState = "yes" | "no" | "unsure";
export type Nis2GovernanceMaturity = "none" | "basic" | "isms_partial" | "isms_established";
