const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.COMPLIANCEHUB_API_BASE_URL ||
  "http://localhost:8000";
const API_KEY =
  process.env.NEXT_PUBLIC_API_KEY ||
  process.env.COMPLIANCEHUB_API_KEY ||
  "tenant-overview-key";
const TENANT_ID =
  process.env.NEXT_PUBLIC_TENANT_ID ||
  process.env.COMPLIANCEHUB_TENANT_ID ||
  "tenant-overview-001";

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

/** Board-fähiger EU AI Act / ISO 42001 Compliance-Readiness-Überblick */
export interface TopCriticalRequirement {
  article: string;
  name: string;
  affected_systems_count: number;
}

export interface AIComplianceOverview {
  tenant_id: string;
  overall_readiness: number;
  high_risk_systems_with_full_controls: number;
  high_risk_systems_with_critical_gaps: number;
  top_critical_requirements: TopCriticalRequirement[];
  deadline: string;
  days_remaining: number;
  nis2_kritis_kpi_mean_percent?: number | null;
  nis2_kritis_systems_full_coverage_ratio?: number;
}

export async function fetchAIComplianceOverview(): Promise<AIComplianceOverview> {
  return apiFetch("/api/v1/ai-governance/compliance/overview");
}

// ─── Board-Level AI Governance KPIs ────────────────────────────────────────────

export interface BoardKpiSummary {
  tenant_id: string;
  ai_systems_total: number;
  active_ai_systems: number;
  high_risk_systems: number;
  open_policy_violations: number;
  board_maturity_score: number;
  compliance_coverage_score: number;
  risk_governance_score: number;
  operational_resilience_score: number;
  responsible_ai_score: number;
  high_risk_systems_without_dpia: number;
  critical_systems_without_owner: number;
  nis2_control_gaps: number;
  nis2_incident_readiness_ratio: number;
  nis2_supplier_risk_coverage_ratio: number;
  iso42001_governance_score: number;
  score_change_vs_last_quarter: number;
  incidents_last_quarter: number;
  complaints_last_quarter: number;
  nis2_kritis_kpi_mean_percent?: number | null;
  nis2_kritis_systems_full_coverage_ratio?: number;
}

export async function fetchBoardKpis(): Promise<BoardKpiSummary> {
  return apiFetch("/api/v1/ai-governance/board-kpis");
}

/** Board-KPI-Alert (NIS2 / EU AI Act / ISO 42001 Schwellenwerte) */
export type AIKpiAlertSeverity = "info" | "warning" | "critical";

export interface AIKpiAlert {
  id: string;
  tenant_id: string;
  kpi_key: string;
  severity: AIKpiAlertSeverity;
  message: string;
  created_at: string;
  resolved_at: string | null;
}

export async function fetchBoardAlerts(): Promise<AIKpiAlert[]> {
  return apiFetch("/api/v1/ai-governance/alerts/board");
}

/** Export-URL für Board-Alerts (JSON/CSV) – für Weiterleitung an CISO/ISB/Vorstand. */
export function fetchBoardAlertsExport(format?: "json" | "csv"): string {
  return `/api/board/alerts/export?format=${format ?? "json"}`;
}

/** Vorstands-/Aufsichtsreport: alle AI-Governance-Kennzahlen gebündelt. */
export interface AIBoardGovernanceReport {
  tenant_id: string;
  generated_at: string;
  period: string;
  kpis: BoardKpiSummary;
  compliance_overview: AIComplianceOverview;
  incidents_overview: AIIncidentOverview;
  supplier_risk_overview: AISupplierRiskOverview;
  alerts: AIKpiAlert[];
}

export async function fetchBoardGovernanceReport(): Promise<AIBoardGovernanceReport> {
  return apiFetch("/api/v1/ai-governance/report/board");
}

/** Download-URL für Board-Report JSON (für Vorstand/SVV/ISB-Reportings). */
export function getBoardReportDownloadUrl(): string {
  return "/api/board/report";
}

/** Download-URL für Board-Report als Markdown (Vorstand/Aufsicht, template-fähig). */
export function getBoardReportMarkdownDownloadUrl(): string {
  return "/api/board/report/markdown";
}

/** Download-URL für Board-KPI-Export (JSON/CSV) – Proxy-Route Next.js. */
export function getBoardKpiExportUrl(format: "json" | "csv" = "json"): string {
  return `/api/board/kpi-export?format=${format}`;
}

// ─── Board-Report Export-Jobs (PDF-/DMS-/SAP-BTP-Integration) ─────────────────

export type BoardReportTargetSystem =
  | "generic_webhook"
  | "sap_btp"
  | "sharepoint"
  | "sap_btp_http"
  | "dms_generic"
  | "datev_dms_prepared";

export type BoardReportExportJobStatus =
  | "pending"
  | "sent"
  | "failed"
  | "not_implemented";

export interface BoardReportExportJobCreate {
  target_system: BoardReportTargetSystem;
  callback_url?: string | null;
  metadata?: Record<string, string> | null;
}

export interface BoardReportExportJob {
  id: string;
  tenant_id: string;
  created_at: string;
  status: BoardReportExportJobStatus;
  target_system: BoardReportTargetSystem;
  callback_url: string | null;
  metadata: Record<string, string> | null;
  error_message: string | null;
  completed_at: string | null;
}

export async function createBoardReportExportJob(
  payload: BoardReportExportJobCreate
): Promise<BoardReportExportJob> {
  return apiFetch("/api/v1/ai-governance/report/board/export-jobs", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchBoardReportExportJobStatus(
  jobId: string
): Promise<BoardReportExportJob> {
  return apiFetch(
    `/api/v1/ai-governance/report/board/export-jobs/${jobId}`
  );
}

// ─── Board-Report Audit-Records (WP-/Prüfungsdokumentation, Audit-Ready) ────────

export type AuditRecordStatus = "draft" | "final";

export type BoardKpiExportJobStatus = "completed" | "failed";

export type KpiExportTargetLabel = "datev" | "dms" | "sap_btp_placeholder";

export interface BoardKpiExportJob {
  id: string;
  tenant_id: string;
  created_at: string;
  completed_at: string | null;
  status: BoardKpiExportJobStatus;
  target_system_label: KpiExportTargetLabel;
  export_format: "json" | "csv";
  metadata: Record<string, string> | null;
  error_message: string | null;
}

export interface BoardReportAuditRecord {
  id: string;
  tenant_id: string;
  report_generated_at: string;
  report_version: string;
  created_at: string;
  created_by: string;
  purpose: string;
  linked_export_job_ids: string[];
  linked_kpi_export_job_ids?: string[];
  status: AuditRecordStatus;
}

export interface BoardReportAuditRecordWithJobs extends BoardReportAuditRecord {
  linked_export_jobs: BoardReportExportJob[];
  linked_kpi_export_jobs?: BoardKpiExportJob[];
}

export interface BoardReportAuditRecordCreate {
  purpose: string;
  status?: AuditRecordStatus;
  linked_export_job_ids?: string[];
  linked_kpi_export_job_ids?: string[];
}

export async function createBoardReportAuditRecord(
  payload: BoardReportAuditRecordCreate
): Promise<BoardReportAuditRecord> {
  return apiFetch("/api/v1/ai-governance/report/board/audit-records", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchBoardReportAuditRecords(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<BoardReportAuditRecord[]> {
  const search = new URLSearchParams();
  if (params?.status) search.set("status", params.status);
  if (params?.limit != null) search.set("limit", String(params.limit));
  if (params?.offset != null) search.set("offset", String(params.offset));
  const q = search.toString();
  return apiFetch(
    `/api/v1/ai-governance/report/board/audit-records${q ? `?${q}` : ""}`
  );
}

export async function fetchBoardReportAuditRecordById(
  auditId: string
): Promise<BoardReportAuditRecordWithJobs> {
  return apiFetch(
    `/api/v1/ai-governance/report/board/audit-records/${auditId}`
  );
}

// ─── Norm-Nachweise (NormEvidenceLinks) ──────────────────────────────────────

export type NormFramework = "EU_AI_ACT" | "NIS2" | "ISO_42001";
export type EvidenceType = "board_report" | "export_job" | "other";

export interface NormEvidenceLink {
  id: string;
  tenant_id: string;
  audit_record_id: string;
  framework: NormFramework;
  reference: string;
  evidence_type: EvidenceType;
  note: string | null;
}

export interface NormEvidenceLinkCreate {
  framework: NormFramework;
  reference: string;
  evidence_type?: EvidenceType;
  note?: string;
}

export async function createNormEvidence(
  auditId: string,
  payload: NormEvidenceLinkCreate | NormEvidenceLinkCreate[]
): Promise<NormEvidenceLink[]> {
  return apiFetch(
    `/api/v1/ai-governance/report/board/audit-records/${auditId}/norm-evidence`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function fetchNormEvidenceByAudit(
  auditId: string
): Promise<NormEvidenceLink[]> {
  return apiFetch(
    `/api/v1/ai-governance/report/board/audit-records/${auditId}/norm-evidence`
  );
}

export type NormEvidenceSuggestion = NormEvidenceLinkCreate;

export async function fetchNormEvidenceDefaults(): Promise<NormEvidenceSuggestion[]> {
  return apiFetch("/api/v1/ai-governance/report/board/norm-evidence-defaults");
}

export interface HighRiskScenarioRecommendedEvidence {
  framework: NormFramework;
  reference: string;
  evidence_type: EvidenceType;
  note?: string | null;
}

export interface HighRiskScenarioProfile {
  id: string;
  label: string;
  description: string;
  recommended_evidence: HighRiskScenarioRecommendedEvidence[];
  recommended_incident_response_maturity_percent?: number | null;
  recommended_supplier_risk_coverage_percent?: number | null;
  recommended_ot_it_segregation_percent?: number | null;
}

export async function fetchHighRiskScenarios(): Promise<HighRiskScenarioProfile[]> {
  return apiFetch("/api/v1/ai-governance/high-risk-scenarios");
}

// ─── AI Governance Incident Drilldown (NIS2 Art. 21/23, ISO 42001) ─────────────

export type IncidentSeverityLevel = "low" | "medium" | "high";

export interface BySeverityEntry {
  severity: IncidentSeverityLevel;
  count: number;
}

export interface AIIncidentOverview {
  tenant_id: string;
  total_incidents_last_12_months: number;
  open_incidents: number;
  major_incidents_last_12_months: number;
  mean_time_to_ack_hours: number | null;
  mean_time_to_recover_hours: number | null;
  by_severity: BySeverityEntry[];
}

export interface AIIncidentBySystem {
  ai_system_id: string;
  ai_system_name: string;
  incident_count: number;
  last_incident_at: string | null;
}

export async function fetchIncidentOverview(): Promise<AIIncidentOverview> {
  return apiFetch("/api/v1/ai-governance/incidents/overview");
}

export async function fetchIncidentsBySystem(): Promise<AIIncidentBySystem[]> {
  return apiFetch("/api/v1/ai-governance/incidents/by-system");
}

// ─── AI Governance Supplier Risk Drilldown (NIS2 Art. 21/24, Supply-Chain) ─────

export type SupplierRiskLevel = "high" | "medium" | "low";

export interface BySupplierRiskLevelEntry {
  risk_level: SupplierRiskLevel;
  systems_with_register: number;
  systems_without_register: number;
}

export interface AISupplierRiskOverview {
  tenant_id: string;
  total_systems_with_suppliers: number;
  systems_without_supplier_risk_register: number;
  critical_suppliers_total: number;
  critical_suppliers_without_controls: number;
  by_risk_level: BySupplierRiskLevelEntry[];
}

export interface AISupplierRiskBySystem {
  ai_system_id: string;
  ai_system_name: string;
  has_supplier_risk_register: boolean;
  supplier_risk_score: number;
}

export async function fetchSupplierRiskOverview(): Promise<AISupplierRiskOverview> {
  return apiFetch("/api/v1/ai-governance/suppliers/overview");
}

export async function fetchSupplierRiskBySystem(): Promise<AISupplierRiskBySystem[]> {
  return apiFetch("/api/v1/ai-governance/suppliers/by-system");
}

// ─── NIS2 / KRITIS KPIs pro AI-System ─────────────────────────────────────────

export type Nis2KritisKpiType =
  | "INCIDENT_RESPONSE_MATURITY"
  | "SUPPLIER_RISK_COVERAGE"
  | "OT_IT_SEGREGATION";

export interface Nis2KritisKpi {
  id: string;
  ai_system_id: string;
  kpi_type: Nis2KritisKpiType;
  value_percent: number;
  evidence_ref: string | null;
  last_reviewed_at: string | null;
}

export interface Nis2KritisKpiRecommended {
  scenario_profile_id: string | null;
  scenario_label: string | null;
  incident_response_maturity_percent: number | null;
  supplier_risk_coverage_percent: number | null;
  ot_it_segregation_percent: number | null;
}

export interface Nis2KritisKpiListResponse {
  kpis: Nis2KritisKpi[];
  recommended: Nis2KritisKpiRecommended | null;
}

export async function fetchNis2KritisKpis(
  aiSystemId: string
): Promise<Nis2KritisKpiListResponse> {
  return apiFetch(`/api/v1/ai-systems/${aiSystemId}/nis2-kritis-kpis`);
}

export interface Nis2KritisKpiUpsertInput {
  kpi_type: Nis2KritisKpiType;
  value_percent: number;
  evidence_ref?: string | null;
  last_reviewed_at?: string | null;
}

export async function upsertNis2KritisKpi(
  aiSystemId: string,
  input: Nis2KritisKpiUpsertInput
): Promise<Nis2KritisKpi> {
  return apiFetch(`/api/v1/ai-systems/${aiSystemId}/nis2-kritis-kpis`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export interface Nis2KritisKpiHistogramBucket {
  range_min_inclusive: number;
  range_max_exclusive: number;
  count: number;
}

export interface Nis2KritisKpiCriticalSystemEntry {
  ai_system_id: string;
  name: string;
  business_unit: string;
  kpi_type: Nis2KritisKpiType;
  value_percent: number;
  detail_href: string;
}

export interface Nis2KritisKpiTypeDrilldown {
  kpi_type: Nis2KritisKpiType;
  histogram: Nis2KritisKpiHistogramBucket[];
  critical_systems: Nis2KritisKpiCriticalSystemEntry[];
}

export interface Nis2KritisKpiDrilldown {
  tenant_id: string;
  generated_at: string;
  top_n: number;
  by_kpi_type: Nis2KritisKpiTypeDrilldown[];
}

export async function fetchNis2KritisKpiDrilldown(
  topN = 5
): Promise<Nis2KritisKpiDrilldown> {
  return apiFetch(
    `/api/v1/nis2-kritis/kpi-drilldown?top_n=${encodeURIComponent(String(topN))}`
  );
}

// ─── EU AI Act Readiness & Governance Actions ─────────────────────────────────

export type ReadinessRequirementTraffic = "red" | "amber" | "green";

export interface ReadinessCriticalRequirement {
  code: string;
  name: string;
  affected_systems_count: number;
  traffic: ReadinessRequirementTraffic;
  priority: number;
}

export interface SuggestedGovernanceAction {
  related_requirement: string;
  title: string;
  rationale: string;
  suggested_priority: number;
}

export type GovernanceActionStatus = "open" | "in_progress" | "done";

export interface AIGovernanceActionRead {
  id: string;
  tenant_id: string;
  related_ai_system_id: string | null;
  related_requirement: string;
  title: string;
  status: GovernanceActionStatus;
  due_date: string | null;
  owner: string | null;
  created_at_utc: string;
  updated_at_utc: string;
}

export interface EUAIActReadinessOverview {
  tenant_id: string;
  deadline: string;
  days_remaining: number;
  overall_readiness: number;
  high_risk_systems_essential_complete: number;
  high_risk_systems_essential_incomplete: number;
  critical_requirements: ReadinessCriticalRequirement[];
  suggested_actions: SuggestedGovernanceAction[];
  open_governance_actions: AIGovernanceActionRead[];
}

export async function fetchEuAiActReadiness(): Promise<EUAIActReadinessOverview> {
  return apiFetch("/api/v1/ai-governance/readiness/eu-ai-act");
}


