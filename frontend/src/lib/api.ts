const API_BASE_URL =
  process.env.COMPLIANCEHUB_API_BASE_URL || "http://localhost:8000";
const API_KEY =
  process.env.COMPLIANCEHUB_API_KEY || "tenant-overview-key";
const TENANT_ID =
  process.env.COMPLIANCEHUB_TENANT_ID || "tenant-overview-001";

async function apiFetch(path: string, init?: RequestInit) {
  const url = `${API_BASE_URL}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: {
      "x-api-key": API_KEY,
      "x-tenant-id": TENANT_ID,
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`API ${path} failed with ${res.status}`);
  }

  return res.json();
}

// Typen grob an eure FastAPI-Modelle angelehnt (snake_case-Backend, aber hier camelCase)
export type RiskLevel = "low" | "limited" | "high";
export type AISystemStatus = "draft" | "inreview" | "active" | "retired";

export interface AISystem {
  id: string;
  name: string;
  description?: string;
  businessunit?: string;
  business_unit?: string;
  risklevel?: RiskLevel;
  risk_level?: RiskLevel;
  aiactcategory?: string;
  ai_act_category?: string;
  gdprdpiarequired?: boolean;
  gdpr_dpia_required?: boolean;
  owneremail?: string;
  owner_email?: string;
  criticality?: string;
  datasensitivity?: string;
  data_sensitivity?: string;
  status?: AISystemStatus;
  createdatutc?: string;
  updatedatutc?: string;
}

export interface Violation {
  id: string;
  tenantid?: string;
  aisystemid: string;
  ruleid: string;
  message: string;
  createdat: string;
}

// Liste aller AI-Systeme für Tenant
export async function fetchTenantAISystems(): Promise<AISystem[]> {
  return apiFetch("/api/v1/ai-systems");
}

// Violations eines Tenants
export async function fetchTenantViolations(): Promise<Violation[]> {
  return apiFetch("/api/v1/violations");
}

// Detail eines AI-Systems
export async function fetchAISystemById(id: string): Promise<AISystem> {
  return apiFetch(`/api/v1/ai-systems/${id}`);
}

// Violations für ein konkretes AI-System
export async function fetchAISystemViolations(
  id: string
): Promise<Violation[]> {
  return apiFetch(`/api/v1/ai-systems/${id}/violations`);
}

// ─── EU AI Act Classification & Gap Analysis ─────────────────────────────────

export type EURiskLevel =
  | "prohibited"
  | "high_risk"
  | "limited_risk"
  | "minimal_risk";

export interface RiskClassification {
  ai_system_id: string;
  risk_level: EURiskLevel;
  classification_path: "annex_i" | "annex_iii" | "transparency" | "none";
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

export interface ClassificationSummary {
  tenant_id: string;
  prohibited: number;
  high_risk: number;
  limited_risk: number;
  minimal_risk: number;
  total: number;
}

export interface ComplianceStatusEntry {
  ai_system_id: string;
  requirement_id: string;
  status: "not_started" | "in_progress" | "completed" | "not_applicable";
  evidence_notes?: string;
  last_updated: string;
  updated_by: string;
}

export interface ComplianceRequirement {
  id: string;
  article: string;
  name: string;
  description: string;
  applies_to: string[];
  weight: number;
}

export interface SystemReadiness {
  ai_system_id: string;
  ai_system_name: string;
  risk_level: string;
  readiness_score: number;
  total_requirements: number;
  completed: number;
  in_progress: number;
  not_started: number;
}

export interface ComplianceDashboard {
  tenant_id: string;
  overall_readiness: number;
  systems: SystemReadiness[];
  deadline: string;
  days_remaining: number;
  urgent_gaps: { ai_system_id: string; ai_system_name: string; requirement_id: string; requirement_name: string; article: string }[];
}

export async function classifyAISystem(
  id: string,
  questionnaire: Record<string, unknown>
): Promise<RiskClassification> {
  return apiFetch(`/api/v1/ai-systems/${id}/classify`, {
    method: "POST",
    body: JSON.stringify(questionnaire),
  });
}

export async function fetchClassification(
  id: string
): Promise<RiskClassification> {
  return apiFetch(`/api/v1/ai-systems/${id}/classification`);
}

export async function fetchClassificationSummary(): Promise<ClassificationSummary> {
  return apiFetch("/api/v1/classifications/summary");
}

export async function fetchSystemCompliance(
  id: string
): Promise<ComplianceStatusEntry[]> {
  return apiFetch(`/api/v1/ai-systems/${id}/compliance`);
}

export async function updateComplianceStatus(
  systemId: string,
  requirementId: string,
  data: { status: string; evidence_notes?: string }
): Promise<ComplianceStatusEntry> {
  return apiFetch(`/api/v1/ai-systems/${systemId}/compliance/${requirementId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function fetchComplianceRequirements(): Promise<ComplianceRequirement[]> {
  return apiFetch("/api/v1/compliance/requirements");
}

export async function fetchComplianceDashboard(): Promise<ComplianceDashboard> {
  return apiFetch("/api/v1/compliance/dashboard");
}

