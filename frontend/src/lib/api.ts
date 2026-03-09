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

