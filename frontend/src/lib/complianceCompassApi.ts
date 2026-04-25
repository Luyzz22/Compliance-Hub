/**
 * Compliance Compass — fusionsbasiertes GRC-Signal (tenant-scoped).
 */

function apiBase(): string {
  return (
    process.env.NEXT_PUBLIC_API_BASE_URL?.trim() ||
    process.env.COMPLIANCEHUB_API_BASE_URL?.trim() ||
    "http://localhost:8000"
  );
}

function apiKey(): string {
  return (
    process.env.NEXT_PUBLIC_API_KEY?.trim() ||
    process.env.COMPLIANCEHUB_API_KEY?.trim() ||
    "tenant-overview-key"
  );
}

const PATH = "/api/v1/governance/compass/snapshot";

export interface CompassPillar {
  key: string;
  label_de: string;
  score_0_100: number;
  weight_in_fusion: number;
  detail_de: string;
}

export interface CompassProvenance {
  readiness_score: number;
  readiness_level: string;
  workflow_open_or_active: number;
  workflow_overdue: number;
  workflow_escalated: number;
  workflow_events_24h: number;
  last_run_completed_at_utc: string | null;
  rule_bundle_version_last_run: string;
  explainability_de: string;
}

export interface ComplianceCompassSnapshot {
  tenant_id: string;
  as_of_utc: string;
  model_version: string;
  fusion_index_0_100: number;
  confidence_0_100: number;
  posture: string;
  narrative_de: string;
  pillars: CompassPillar[];
  provenance: CompassProvenance;
  privacy_de: string;
}

export async function fetchComplianceCompass(
  tenantId: string
): Promise<ComplianceCompassSnapshot> {
  const r = await fetch(`${apiBase()}${PATH}`, {
    headers: {
      "x-api-key": apiKey(),
      "x-tenant-id": tenantId,
    },
    next: { revalidate: 0 },
  });
  if (!r.ok) {
    throw new Error(`Compliance Compass ${r.status}`);
  }
  return (await r.json()) as ComplianceCompassSnapshot;
}
