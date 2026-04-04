/**
 * Types for tenant board/readiness API snapshots (no server-only).
 * Used by fetch layer, gap logic, and advisor export.
 */

export type RawAISystemRow = {
  id: string;
  name: string;
  owner_email?: string | null;
  gdpr_dpia_required?: boolean;
  has_incident_runbook?: boolean;
  has_backup_runbook?: boolean;
  has_supplier_risk_register?: boolean;
  updated_at_utc?: string;
};

export type RawComplianceStatusEntry = {
  requirement_id: string;
  status: string;
};

export type RawSystemReadiness = {
  ai_system_id: string;
  ai_system_name: string;
  risk_level: string;
  readiness_score?: number;
};

export type RawComplianceDashboard = {
  tenant_id: string;
  systems: RawSystemReadiness[];
};

export type RawAIComplianceOverview = {
  tenant_id: string;
  overall_readiness?: number;
  nis2_kritis_kpi_mean_percent?: number | null;
  nis2_kritis_systems_full_coverage_ratio?: number;
};

export type RawEuAIActReadinessOverview = {
  tenant_id: string;
  overall_readiness?: number;
  high_risk_systems_essential_complete?: number;
  high_risk_systems_essential_incomplete?: number;
};

export type RawTenantSetupStatus = {
  tenant_id: string;
  policies_published?: boolean;
  nis2_kpis_seeded?: boolean;
  evidence_attached?: boolean;
  classification_completed?: boolean;
  completed_steps?: number;
  total_steps?: number;
};

export type RawTenantAIGovernanceSetup = {
  tenant_id?: string;
  compliance_scopes?: string[];
  governance_roles?: Record<string, string>;
  active_frameworks?: string[];
  progress_steps?: number[];
};

export type RawBoardReportListItem = {
  id: string;
  title: string;
  created_at: string;
};

export type RawAIActDocListItem = {
  section_key: string;
  status: string;
  doc?: { version?: number; updated_at?: string } | null;
};

export type RawAIActDocListResponse = {
  ai_system_id: string;
  items?: RawAIActDocListItem[];
};

export type TenantBoardReadinessRaw = {
  tenant_id: string;
  fetch_ok: boolean;
  ai_systems: RawAISystemRow[];
  compliance_by_system: Record<string, RawComplianceStatusEntry[]>;
  ai_act_doc_items_by_system: Record<string, RawAIActDocListItem[]>;
  compliance_dashboard: RawComplianceDashboard | null;
  eu_ai_act_readiness: RawEuAIActReadinessOverview | null;
  ai_compliance_overview: RawAIComplianceOverview | null;
  setup_status: RawTenantSetupStatus | null;
  ai_governance_setup: RawTenantAIGovernanceSetup | null;
  board_reports: RawBoardReportListItem[];
  ai_act_docs_errors: Record<string, boolean>;
};
