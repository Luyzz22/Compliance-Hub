import { featureAdvisorWorkspace } from "./config";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.COMPLIANCEHUB_API_BASE_URL ||
  "http://localhost:8000";
const API_KEY =
  process.env.NEXT_PUBLIC_API_KEY ||
  process.env.COMPLIANCEHUB_API_KEY ||
  "tenant-overview-key";
export const TENANT_ID =
  process.env.NEXT_PUBLIC_TENANT_ID ||
  process.env.COMPLIANCEHUB_TENANT_ID ||
  "tenant-overview-001";

function tenantRequestHeaders(
  tenantId: string,
  initHeaders?: HeadersInit,
  options?: { json?: boolean },
): Record<string, string> {
  const h: Record<string, string> = {
    "x-api-key": API_KEY,
    "x-tenant-id": tenantId,
  };
  const opa = process.env.NEXT_PUBLIC_OPA_USER_ROLE?.trim();
  if (opa) {
    h["x-opa-user-role"] = opa;
  }
  if (options?.json !== false) {
    h["Content-Type"] = "application/json";
  }
  if (initHeaders) {
    if (initHeaders instanceof Headers) {
      initHeaders.forEach((v, k) => {
        h[k] = v;
      });
    } else if (Array.isArray(initHeaders)) {
      for (const [k, v] of initHeaders) {
        h[k] = v;
      }
    } else {
      Object.assign(h, initHeaders);
    }
  }
  return h;
}

async function tenantApiFetch(path: string, tenantId: string, init?: RequestInit) {
  const url = `${API_BASE_URL}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: tenantRequestHeaders(tenantId, init?.headers, { json: true }),
    cache: "no-store",
  });

  if (!res.ok) {
    if (res.status === 403) {
      throw new Error(
        "Zugriff verweigert (HTTP 403). Häufig bei Demomandanten: schreibende Aktionen sind " +
          "deaktiviert (read-only). Lesende Aufrufe und vorgefüllte Reports bleiben nutzbar.",
      );
    }
    throw new Error(`API ${path} failed with ${res.status}`);
  }

  return res.json();
}

/** Tenant-authenticated GET/POST ohne JSON-Body (z. B. Export-Download). */
export async function tenantApiFetchResponse(
  path: string,
  tenantId: string,
  init?: RequestInit,
): Promise<Response> {
  const url = `${API_BASE_URL}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: tenantRequestHeaders(tenantId, init?.headers, { json: false }),
    cache: "no-store",
  });
  if (!res.ok) {
    if (res.status === 403) {
      throw new Error(
        "Zugriff verweigert (HTTP 403). Evidence-Export erfordert Berechtigung view_ai_evidence und aktiviertes Feature.",
      );
    }
    throw new Error(`API ${path} failed with ${res.status}`);
  }
  return res;
}

export type WorkspaceModeDto = "production" | "demo" | "playground";

export interface TenantWorkspaceMetaDto {
  tenant_id: string;
  display_name: string;
  is_demo: boolean;
  demo_playground: boolean;
  mutation_blocked: boolean;
  workspace_mode: WorkspaceModeDto;
  mode_label: string;
  mode_hint: string;
  demo_mode_feature_enabled: boolean;
  /** Backend COMPLIANCEHUB_FEATURE_AI_ACT_EVIDENCE_VIEWS. */
  feature_ai_act_evidence_views?: boolean;
  /** OPA view_ai_evidence (gleiche Rollenauflösung wie Evidence-API). */
  can_view_ai_evidence?: boolean;
}

export async function fetchTenantWorkspaceMeta(tenantId: string): Promise<TenantWorkspaceMetaDto> {
  return tenantApiFetch("/api/v1/workspace/tenant-meta", tenantId) as Promise<TenantWorkspaceMetaDto>;
}

/** Workspace-Feature-Telemetrie (GET → workspace_feature_used; Server setzt workspace_mode/actor_type). */
export async function logDemoFeatureUsed(tenantId: string, featureKey: string): Promise<void> {
  const k = encodeURIComponent(featureKey);
  await tenantApiFetch(`/api/v1/workspace/feature-used?feature_key=${k}`, tenantId);
}

// —— AI Act Evidence (read-only, Metadaten) ————————————————————————————————

export interface AiEvidenceEventListItemDto {
  event_id: string;
  timestamp: string;
  event_type: string;
  tenant_id: string;
  user_role: string;
  source: string;
  summary_de: string;
  confidence_level?: string | null;
  purpose?: string | null;
  system_id?: string | null;
  risk_category?: string | null;
  input_source?: string | null;
  output_target?: string | null;
}

export interface AiEvidenceEventListResponseDto {
  items: AiEvidenceEventListItemDto[];
  total: number;
  limit: number;
  offset: number;
}

export type AiEvidenceExportFormat = "csv" | "json";

export interface AiActEvidenceListQuery {
  from_ts?: string;
  to_ts?: string;
  /** Komma-separierte Backend-event_types */
  event_types?: string;
  confidence_level?: string;
  limit?: number;
  offset?: number;
}

export type AiActEvidenceFilterQuery = Omit<AiActEvidenceListQuery, "limit" | "offset">;

function buildAiActEvidenceFilterParams(
  tenantId: string,
  q: AiActEvidenceFilterQuery,
): URLSearchParams {
  const params = new URLSearchParams();
  params.set("tenant_id", tenantId);
  if (q.from_ts) {
    params.set("from_ts", q.from_ts);
  }
  if (q.to_ts) {
    params.set("to_ts", q.to_ts);
  }
  if (q.event_types) {
    params.set("event_types", q.event_types);
  }
  if (q.confidence_level) {
    params.set("confidence_level", q.confidence_level);
  }
  return params;
}

function buildAiActEvidenceQuery(tenantId: string, q: AiActEvidenceListQuery): string {
  const params = buildAiActEvidenceFilterParams(tenantId, q);
  params.set("limit", String(q.limit ?? 50));
  params.set("offset", String(q.offset ?? 0));
  return params.toString();
}

export async function fetchAiActEvidenceEvents(
  tenantId: string,
  q: AiActEvidenceListQuery,
): Promise<AiEvidenceEventListResponseDto> {
  const qs = buildAiActEvidenceQuery(tenantId, q);
  return tenantApiFetch(`/api/v1/evidence/ai-act/events?${qs}`, tenantId) as Promise<AiEvidenceEventListResponseDto>;
}

export interface AiEvidenceRagScoreAuditRowDto {
  doc_id: string;
  bm25_score: number;
  embedding_score: number;
  combined_score: number;
  rag_scope: string;
  is_tenant_guidance: boolean;
}

export interface AiEvidenceRagDetailSectionDto {
  query_sha256?: string | null;
  citation_doc_ids: string[];
  tenant_guidance_citation_count: number;
  confidence_level?: string | null;
  trace_id?: string | null;
  span_id?: string | null;
  citation_count: number;
  retrieval_mode?: string | null;
  score_audit?: AiEvidenceRagScoreAuditRowDto[];
}

export interface AiEvidenceBoardReportWorkflowDetailSectionDto {
  workflow_id: string;
  task_queue?: string | null;
  status_hint?: string | null;
}

export interface AiEvidenceBoardReportCompletedDetailSectionDto {
  report_id: string;
  temporal_workflow_id?: string | null;
  temporal_run_id?: string | null;
  audience_type: string;
  activities_executed: string[];
  title: string;
}

export interface AiEvidenceLlmDetailSectionDto {
  action_name?: string | null;
  task_type?: string | null;
  contract_schema?: string | null;
  error_class?: string | null;
  guardrail_flags?: Record<string, string> | null;
}

export interface AiEvidenceEventDetailDto {
  event_id: string;
  timestamp: string;
  event_type: string;
  tenant_id: string;
  user_role: string;
  source: string;
  summary_de: string;
  purpose?: string | null;
  system_id?: string | null;
  risk_category?: string | null;
  input_source?: string | null;
  output_target?: string | null;
  rag?: AiEvidenceRagDetailSectionDto | null;
  board_report_workflow?: AiEvidenceBoardReportWorkflowDetailSectionDto | null;
  board_report_completed?: AiEvidenceBoardReportCompletedDetailSectionDto | null;
  llm?: AiEvidenceLlmDetailSectionDto | null;
}

export async function fetchAiActEvidenceEventDetail(
  tenantId: string,
  eventId: string,
): Promise<AiEvidenceEventDetailDto> {
  const params = new URLSearchParams({ tenant_id: tenantId });
  const enc = encodeURIComponent(eventId);
  return tenantApiFetch(
    `/api/v1/evidence/ai-act/events/${enc}?${params.toString()}`,
    tenantId,
  ) as Promise<AiEvidenceEventDetailDto>;
}

export async function downloadAiActEvidenceExport(
  tenantId: string,
  format: AiEvidenceExportFormat,
  filters: AiActEvidenceFilterQuery,
): Promise<Blob> {
  const params = buildAiActEvidenceFilterParams(tenantId, filters);
  params.set("format", format);
  const res = await tenantApiFetchResponse(
    `/api/v1/evidence/ai-act/export?${params.toString()}`,
    tenantId,
    { method: "GET" },
  );
  return res.blob();
}

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
export async function fetchTenantAISystems(tenantId: string = TENANT_ID): Promise<AISystem[]> {
  return tenantApiFetch("/api/v1/ai-systems", tenantId);
}

export interface AIImportRowError {
  row_number: number;
  message: string;
}

export interface AIImportResult {
  total_rows: number;
  imported_count: number;
  failed_count: number;
  errors: AIImportRowError[];
}

/** Multipart-Upload der Stammdaten-Datei (CSV oder .xlsx). */
export async function importAiSystemsFile(file: File): Promise<AIImportResult> {
  const url = `${API_BASE_URL}/api/v1/ai-systems/import`;
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "x-api-key": API_KEY,
      "x-tenant-id": TENANT_ID,
    },
    body: formData,
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(
      `Import fehlgeschlagen (${res.status}): ${text || res.statusText}`
    );
  }
  return res.json() as Promise<AIImportResult>;
}

export interface EvidenceFile {
  id: string;
  tenant_id: string;
  ai_system_id?: string | null;
  audit_record_id?: string | null;
  action_id?: string | null;
  filename_original: string;
  content_type: string;
  size_bytes: number;
  uploaded_by: string;
  norm_framework?: string | null;
  norm_reference?: string | null;
  created_at: string;
  updated_at: string;
}

export type EvidenceListFilter =
  | { ai_system_id: string }
  | { audit_record_id: string }
  | { action_id: string };

export async function fetchEvidenceList(
  filter: EvidenceListFilter
): Promise<EvidenceFile[]> {
  const params = new URLSearchParams();
  if ("ai_system_id" in filter) {
    params.set("ai_system_id", filter.ai_system_id);
  }
  if ("audit_record_id" in filter) {
    params.set("audit_record_id", filter.audit_record_id);
  }
  if ("action_id" in filter) {
    params.set("action_id", filter.action_id);
  }
  const res = await fetch(
    `${API_BASE_URL}/api/v1/evidence?${params.toString()}`,
    {
      headers: {
        "x-api-key": API_KEY,
        "x-tenant-id": TENANT_ID,
      },
      cache: "no-store",
    }
  );
  if (!res.ok) {
    throw new Error(`Evidence list failed: ${res.status}`);
  }
  const body = (await res.json()) as { items: EvidenceFile[] };
  return body.items;
}

export async function uploadEvidenceFile(
  file: File,
  options: {
    ai_system_id?: string;
    audit_record_id?: string;
    action_id?: string;
    norm_framework?: string;
    norm_reference?: string;
    uploadedBy?: string;
  }
): Promise<EvidenceFile> {
  const fd = new FormData();
  fd.append("file", file);
  if (options.ai_system_id) {
    fd.append("ai_system_id", options.ai_system_id);
  }
  if (options.audit_record_id) {
    fd.append("audit_record_id", options.audit_record_id);
  }
  if (options.action_id) {
    fd.append("action_id", options.action_id);
  }
  if (options.norm_framework) {
    fd.append("norm_framework", options.norm_framework);
  }
  if (options.norm_reference) {
    fd.append("norm_reference", options.norm_reference);
  }
  const headers: Record<string, string> = {
    "x-api-key": API_KEY,
    "x-tenant-id": TENANT_ID,
  };
  if (options.uploadedBy?.trim()) {
    headers["x-uploaded-by"] = options.uploadedBy.trim();
  }
  const res = await fetch(`${API_BASE_URL}/api/v1/evidence/uploads`, {
    method: "POST",
    headers,
    body: fd,
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Evidence upload failed (${res.status}): ${text || res.statusText}`);
  }
  return res.json() as Promise<EvidenceFile>;
}

export async function downloadEvidenceBlob(evidenceId: string): Promise<Blob> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/evidence/${encodeURIComponent(evidenceId)}/download`,
    {
      headers: {
        "x-api-key": API_KEY,
        "x-tenant-id": TENANT_ID,
      },
      cache: "no-store",
    }
  );
  if (!res.ok) {
    throw new Error(`Evidence download failed: ${res.status}`);
  }
  return res.blob();
}

export async function deleteEvidenceFile(evidenceId: string): Promise<void> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/evidence/${encodeURIComponent(evidenceId)}`,
    {
      method: "DELETE",
      headers: {
        "x-api-key": API_KEY,
        "x-tenant-id": TENANT_ID,
      },
      cache: "no-store",
    }
  );
  if (res.status === 403) {
    throw new Error(
      "Löschen ist für diesen API-Key nicht freigeschaltet (COMPLIANCEHUB_EVIDENCE_DELETE_API_KEYS)."
    );
  }
  if (!res.ok) {
    throw new Error(`Evidence delete failed: ${res.status}`);
  }
}

// Violations eines Tenants
export async function fetchTenantViolations(tenantId: string = TENANT_ID): Promise<Violation[]> {
  return tenantApiFetch("/api/v1/violations", tenantId);
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

/** Optionale Kennzahlen zu NIS2-/KRITIS-KPI-Alerts (Ist/Soll, KPI-Typ, Top-Systeme). */
export interface AIKpiAlertMetadata {
  current_percent?: number | null;
  threshold_percent?: number | null;
  kpi_type?: string | null;
  affected_system_ids?: string[];
  coverage_ratio_current?: number | null;
  coverage_ratio_threshold?: number | null;
}

export interface AIKpiAlert {
  id: string;
  tenant_id: string;
  kpi_key: string;
  severity: AIKpiAlertSeverity;
  message: string;
  created_at: string;
  resolved_at: string | null;
  alert_metadata?: AIKpiAlertMetadata | null;
}

export async function fetchBoardAlerts(): Promise<AIKpiAlert[]> {
  return apiFetch("/api/v1/ai-governance/alerts/board");
}

/** Export-URL für Board-Alerts (JSON/CSV) – für Weiterleitung an CISO/ISB/Vorstand. */
export function fetchBoardAlertsExport(format?: "json" | "csv"): string {
  return `/api/board/alerts/export?format=${format ?? "json"}`;
}

/** Gewichtete OAMI-Incident-Subtypen (Board-Markdown / spätere Charts). */
export interface OamiIncidentSubtypeProfileDto {
  incident_weighted_share_safety: number;
  incident_weighted_share_availability: number;
  incident_weighted_share_other: number;
  incident_count_by_category: {
    safety: number;
    availability: number;
    other: number;
  };
  oami_subtype_narrative_de: string;
  chart_note_de: string;
  category_labels_de: Record<string, string>;
}

/** Incident-Drilldown je KI-System / Lieferant (Advisor & Mandant, siehe docs/incidents-supplier-drilldowns.md). */
export interface TenantIncidentDrilldownItemDto {
  ai_system_id: string;
  ai_system_name: string;
  supplier_label_de: string;
  event_source: string;
  incident_total_90d: number;
  incident_count_by_category: {
    safety: number;
    availability: number;
    other: number;
  };
  weighted_incident_share_safety: number;
  weighted_incident_share_availability: number;
  weighted_incident_share_other: number;
  oami_local_hint_de: string;
}

export interface TenantIncidentDrilldownOutDto {
  tenant_id: string;
  window_days: number;
  systems_with_runtime_events: number;
  systems_with_incidents: number;
  items: TenantIncidentDrilldownItemDto[];
}

/** OAMI-Abschnitt im Board-Governance-Report (90-Tage-Laufzeitfenster). */
export interface BoardOperationalMonitoringSectionDto {
  index_value: number;
  level: string;
  window_days: number;
  has_data: boolean;
  systems_scored: number;
  summary_de: string;
  drivers_de: string[];
  oami_incident_subtype_profile?: OamiIncidentSubtypeProfileDto | null;
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
  operational_monitoring?: BoardOperationalMonitoringSectionDto | null;
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

export interface Nis2KritisKpiSuggestion {
  kpi_type: Nis2KritisKpiType;
  suggested_value_percent: number;
  confidence: number;
  rationale: string;
}

export interface Nis2KritisKpiSuggestionResponse {
  ai_system_id: string;
  suggestions: Nis2KritisKpiSuggestion[];
}

export async function postNis2KritisKpiSuggestions(
  aiSystemId: string,
  freeText: string
): Promise<Nis2KritisKpiSuggestionResponse> {
  return apiFetch(
    `/api/v1/ai-systems/${encodeURIComponent(aiSystemId)}/nis2-kritis-kpi-suggestions`,
    {
      method: "POST",
      body: JSON.stringify({ free_text: freeText }),
    }
  );
}

export interface ExplainTenantContextInput {
  industry?: string | null;
  nis2_scope?: string | null;
  high_risk_systems_count?: number | null;
}

export interface ExplainRequestInput {
  kpi_key: string;
  current_value?: number | null;
  value_is_percent?: boolean;
  alert_key?: string | null;
  threshold_warning?: number | null;
  threshold_critical?: number | null;
  tenant_context?: ExplainTenantContextInput | null;
}

export interface ExplainResponsePayload {
  title: string;
  summary: string;
  why_it_matters: string[];
  suggested_actions: string[];
}

export async function postAiGovernanceExplain(
  body: ExplainRequestInput
): Promise<ExplainResponsePayload> {
  return apiFetch("/api/v1/ai-governance/explain", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export interface ActionDraftRequirementInput {
  framework: string;
  reference: string;
  gap_description: string;
}

export interface AIGovernanceActionDraftRequestInput {
  ai_system_id?: string | null;
  requirements: ActionDraftRequirementInput[];
}

export interface AIGovernanceActionDraft {
  title: string;
  description: string;
  framework: string;
  reference: string;
  priority: string;
  suggested_role: string;
}

export interface AIGovernanceActionDraftResponsePayload {
  ai_system_id: string | null;
  drafts: AIGovernanceActionDraft[];
}

export async function postAiGovernanceActionDrafts(
  body: AIGovernanceActionDraftRequestInput
): Promise<AIGovernanceActionDraftResponsePayload> {
  return apiFetch("/api/v1/ai-governance/action-drafts", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ─── EU AI Act – Dokumentationsbausteine ─────────────────────────────────────

export type AIActDocSectionKey =
  | "RISK_MANAGEMENT"
  | "DATA_GOVERNANCE"
  | "MONITORING_LOGGING"
  | "HUMAN_OVERSIGHT"
  | "TECHNICAL_ROBUSTNESS";

export interface AIActDocPayload {
  id: string;
  tenant_id: string;
  ai_system_id: string;
  section_key: AIActDocSectionKey;
  title: string;
  content_markdown: string;
  version: number;
  content_source?: "manual" | "ai_generated" | null;
  created_at: string;
  created_by: string;
  updated_at: string;
  updated_by: string;
}

export interface AIActDocListItemPayload {
  section_key: AIActDocSectionKey;
  default_title: string;
  doc: AIActDocPayload | null;
  status: string;
}

export interface AIActDocListResponsePayload {
  ai_system_id: string;
  items: AIActDocListItemPayload[];
}

export async function fetchAiActDocList(
  aiSystemId: string
): Promise<AIActDocListResponsePayload> {
  return apiFetch(`/api/v1/ai-systems/${encodeURIComponent(aiSystemId)}/ai-act-docs`);
}

export async function postAiActDocDraft(
  aiSystemId: string,
  sectionKey: AIActDocSectionKey
): Promise<AIActDocPayload> {
  return apiFetch(
    `/api/v1/ai-systems/${encodeURIComponent(aiSystemId)}/ai-act-docs/${sectionKey}/draft`,
    { method: "POST" }
  );
}

export async function persistAiActDocSection(
  aiSystemId: string,
  sectionKey: AIActDocSectionKey,
  body: {
    title: string;
    content_markdown: string;
    content_source?: "manual" | "ai_generated" | null;
  }
): Promise<AIActDocPayload> {
  return apiFetch(
    `/api/v1/ai-systems/${encodeURIComponent(aiSystemId)}/ai-act-docs/${sectionKey}`,
    {
      method: "POST",
      body: JSON.stringify(body),
    }
  );
}

export async function downloadAiActDocumentationMarkdown(
  aiSystemId: string
): Promise<void> {
  const url = `${API_BASE_URL}/api/v1/ai-systems/${encodeURIComponent(aiSystemId)}/ai-act-docs/export?format=markdown`;
  const res = await fetch(url, {
    method: "GET",
    headers: {
      "x-api-key": API_KEY,
      "x-tenant-id": TENANT_ID,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Export fehlgeschlagen (${res.status})`);
  }
  const blob = await res.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `ai-act-documentation-${aiSystemId}.md`;
  a.click();
  URL.revokeObjectURL(a.href);
}

export type WhatIfBoardKpiType =
  | "INCIDENT_RESPONSE_MATURITY"
  | "SUPPLIER_RISK_COVERAGE"
  | "OT_IT_SEGREGATION"
  | "EU_AI_ACT_CONTROL_FULFILLMENT";

export interface WhatIfKpiAdjustmentInput {
  ai_system_id: string;
  kpi_type: WhatIfBoardKpiType;
  target_value_percent: number;
}

export interface WhatIfScenarioInputPayload {
  kpi_adjustments: WhatIfKpiAdjustmentInput[];
}

export interface BoardKpiSummaryPayload {
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
  nis2_kritis_kpi_mean_percent: number | null;
  nis2_kritis_systems_full_coverage_ratio: number;
}

export interface AIComplianceOverviewPayload {
  tenant_id: string;
  overall_readiness: number;
  high_risk_systems_with_full_controls: number;
  high_risk_systems_with_critical_gaps: number;
  top_critical_requirements: { article: string; name: string; affected_systems_count: number }[];
  deadline: string;
  days_remaining: number;
  nis2_kritis_kpi_mean_percent: number | null;
  nis2_kritis_systems_full_coverage_ratio: number;
}

export interface WhatIfScenarioResultPayload {
  original_readiness: number;
  simulated_readiness: number;
  original_board_kpis: BoardKpiSummaryPayload;
  simulated_board_kpis: BoardKpiSummaryPayload;
  original_compliance_overview: AIComplianceOverviewPayload;
  simulated_compliance_overview: AIComplianceOverviewPayload;
  original_alerts_count: number;
  simulated_alerts_count: number;
  alert_signatures_resolved: string[];
  alert_signatures_new: string[];
}

export async function postWhatIfBoardImpact(
  body: WhatIfScenarioInputPayload
): Promise<WhatIfScenarioResultPayload> {
  return apiFetch("/api/v1/ai-governance/what-if/board-impact", {
    method: "POST",
    body: JSON.stringify(body),
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
  requirement_id?: string | null;
  related_ai_system_ids?: string[];
  linked_governance_action_ids?: string[];
  open_actions_count_for_requirement?: number;
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

export interface AIGovernanceActionCreateInput {
  related_ai_system_id?: string | null;
  related_requirement: string;
  title: string;
  status?: GovernanceActionStatus;
  due_date?: string | null;
  owner?: string | null;
}

export async function createAIGovernanceAction(
  input: AIGovernanceActionCreateInput
): Promise<AIGovernanceActionRead> {
  return apiFetch("/api/v1/ai-governance/actions", {
    method: "POST",
    body: JSON.stringify({
      related_ai_system_id: input.related_ai_system_id ?? null,
      related_requirement: input.related_requirement,
      title: input.title,
      status: input.status ?? "open",
      due_date: input.due_date ?? null,
      owner: input.owner ?? null,
    }),
  });
}

// ─── Guided Setup (Tenant-Onboarding) ─────────────────────────────────────────

export interface TenantSetupStatus {
  tenant_id: string;
  ai_inventory_completed: boolean;
  classification_completed: boolean;
  classification_coverage_ratio: number;
  nis2_kpis_seeded: boolean;
  policies_published: boolean;
  actions_defined: boolean;
  evidence_attached: boolean;
  eu_ai_act_readiness_baseline_created: boolean;
  completed_steps: number;
  total_steps: number;
}

export async function fetchTenantSetupStatus(
  tenantId: string = TENANT_ID
): Promise<TenantSetupStatus> {
  const tid = encodeURIComponent(tenantId);
  return tenantApiFetch(`/api/v1/tenants/${tid}/setup-status`, tenantId);
}

// ─── AI-Governance-Setup-Wizard ──────────────────────────────────────────────

export interface TenantAiGovernanceSetupDto {
  tenant_id: string;
  tenant_kind: "enterprise" | "advisor" | null;
  compliance_scopes: string[];
  governance_roles: Record<string, string>;
  active_frameworks: string[];
  steps_marked_complete: number[];
  flags: Record<string, boolean>;
  progress_steps: number[];
}

export async function fetchTenantAiGovernanceSetup(
  tenantId: string,
): Promise<TenantAiGovernanceSetupDto> {
  const tid = encodeURIComponent(tenantId);
  return tenantApiFetch(`/api/v1/tenants/${tid}/ai-governance-setup`, tenantId);
}

export async function putTenantAiGovernanceSetup(
  tenantId: string,
  body: {
    tenant_kind?: "enterprise" | "advisor" | null;
    compliance_scopes?: string[];
    governance_roles?: Record<string, string>;
    active_frameworks?: string[];
    mark_steps_complete?: number[];
    flags?: Record<string, boolean>;
  },
): Promise<TenantAiGovernanceSetupDto> {
  const tid = encodeURIComponent(tenantId);
  return tenantApiFetch(`/api/v1/tenants/${tid}/ai-governance-setup`, tenantId, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export async function createTenantAiSystem(
  tenantId: string,
  body: {
    id: string;
    name: string;
    description: string;
    business_unit: string;
    risk_level: string;
    ai_act_category: string;
    gdpr_dpia_required: boolean;
    owner_email?: string | null;
    criticality?: string;
    data_sensitivity?: string;
    has_incident_runbook?: boolean;
    has_supplier_risk_register?: boolean;
    has_backup_runbook?: boolean;
  },
): Promise<AISystem> {
  return tenantApiFetch("/api/v1/ai-systems", tenantId, {
    method: "POST",
    body: JSON.stringify({
      id: body.id,
      name: body.name,
      description: body.description,
      business_unit: body.business_unit,
      risk_level: body.risk_level,
      ai_act_category: body.ai_act_category,
      gdpr_dpia_required: body.gdpr_dpia_required,
      owner_email: body.owner_email ?? null,
      criticality: body.criticality ?? "medium",
      data_sensitivity: body.data_sensitivity ?? "internal",
      has_incident_runbook: body.has_incident_runbook ?? false,
      has_supplier_risk_register: body.has_supplier_risk_register ?? false,
      has_backup_runbook: body.has_backup_runbook ?? false,
    }),
  });
}

// ─── Advisor-Portfolio (Multi-Mandant / Berater) ─────────────────────────────

export const ADVISOR_ID_FROM_ENV =
  process.env.NEXT_PUBLIC_ADVISOR_ID?.trim() || "";

export function isAdvisorNavEnabled(): boolean {
  if (!featureAdvisorWorkspace()) return false;
  if (process.env.NEXT_PUBLIC_SHOW_ADVISOR_NAV === "1") return true;
  return ADVISOR_ID_FROM_ENV.length > 0;
}

export interface ReadinessDimensionDto {
  normalized: number;
  score_0_100: number;
}

export interface ReadinessScoreDimensionsDto {
  setup: ReadinessDimensionDto;
  coverage: ReadinessDimensionDto;
  kpi: ReadinessDimensionDto;
  gaps: ReadinessDimensionDto;
  reporting: ReadinessDimensionDto;
}

export interface ReadinessScoreResponseDto {
  tenant_id: string;
  score: number;
  level: "basic" | "managed" | "embedded";
  interpretation: string;
  dimensions: ReadinessScoreDimensionsDto;
}

export interface ReadinessScoreSummaryDto {
  score: number;
  level: "basic" | "managed" | "embedded";
}

/** Strukturierte KI-Erklärung; Level = API-Enums (UI-Labels via governanceMaturityDeCopy). */
export interface ReadinessExplanationStructuredDto {
  score: number;
  level: "basic" | "managed" | "embedded";
  short_reason: string;
  drivers_positive: string[];
  drivers_negative: string[];
  regulatory_focus: string;
}

export interface OperationalMonitoringExplanationStructuredDto {
  index: number | null;
  level: "low" | "medium" | "high" | null;
  recent_incidents_summary: string;
  monitoring_gaps: string[];
  improvement_suggestions: string[];
  /** Server: Subtype safety_violation im 90-Tage-Fenster (Laufzeit-Incidents). */
  safety_related_incidents_90d?: number | null;
  /** Server: Subtype availability_incident. */
  availability_incidents_90d?: number | null;
  /** Server: Kurz-Hinweis ohne numerische Gewichte. */
  oami_subtype_hint_de?: string | null;
}

export interface ReadinessScoreExplainResponseDto {
  explanation: string;
  provider: string;
  model_id: string;
  readiness_explanation?: ReadinessExplanationStructuredDto | null;
  operational_monitoring_explanation?: OperationalMonitoringExplanationStructuredDto | null;
}

export interface AdvisorTenantGovernanceBriefDto {
  wizard_progress_count: number;
  wizard_steps_total: number;
  active_framework_keys: string[];
  cross_reg_mean_coverage_percent: number | null;
  regulatory_gap_count: number;
  nis2_critical_ai_count: number;
}

/** Board-kompatibler Kern + Berater-Felder (API-Enums wie Backend). */
export interface GovernanceMaturitySummaryDto {
  readiness: { score: number; level: string; short_reason: string };
  activity: { index: number; level: string; short_reason: string };
  operational_monitoring: {
    index: number | null;
    level: string | null;
    short_reason: string;
  };
  overall_assessment: {
    level: string;
    short_summary: string;
    key_risks: string[];
    key_strengths: string[];
  };
}

export interface AdvisorGovernanceMaturityBriefDto {
  governance_maturity_summary: GovernanceMaturitySummaryDto;
  recommended_focus_areas: string[];
  suggested_next_steps_window: string;
  client_ready_paragraph_de?: string | null;
}

export interface AdvisorPortfolioTenantEntry {
  tenant_id: string;
  tenant_name: string;
  industry?: string | null;
  country?: string | null;
  /** Aus Mandanten-nis2_scope normalisiert (none | important_entity | essential_entity). */
  nis2_entity_category?: "none" | "important_entity" | "essential_entity";
  /** KRITIS-Sektorschlüssel aus Stammdaten, falls gepflegt. */
  kritis_sector_key?: string | null;
  /** Mind. ein strukturiertes Incident in den letzten 90 Tagen. */
  recent_incidents_90d?: boolean;
  /** Aggregierte Last (low | medium | high), ohne Einzelfallinhalte. */
  incident_burden_level?: "low" | "medium" | "high";
  eu_ai_act_readiness: number;
  nis2_kritis_kpi_mean_percent?: number | null;
  nis2_kritis_systems_full_coverage_ratio: number;
  high_risk_systems_count: number;
  open_governance_actions_count: number;
  setup_completed_steps: number;
  setup_total_steps: number;
  setup_progress_ratio: number;
  governance_brief?: AdvisorTenantGovernanceBriefDto | null;
  readiness_summary?: ReadinessScoreSummaryDto | null;
  governance_activity_summary?: { index: number; level: string } | null;
  operational_monitoring_summary?: {
    index: number | null;
    level: string | null;
    safety_related_runtime_incidents_90d?: number;
    availability_runtime_incidents_90d?: number;
    oami_operational_hint_de?: string | null;
  } | null;
  governance_maturity_advisor_brief?: AdvisorGovernanceMaturityBriefDto | null;
  advisor_priority?: "high" | "medium" | "low";
  advisor_priority_sort_key?: number;
  advisor_priority_explanation_de?: string;
  maturity_scenario_hint?: "a" | "b" | "c" | "d" | null;
  primary_focus_tag_de?: string;
}

export interface AdvisorPortfolioResponse {
  advisor_id: string;
  generated_at_utc: string;
  tenants: AdvisorPortfolioTenantEntry[];
}

export async function fetchAdvisorPortfolio(
  advisorId: string
): Promise<AdvisorPortfolioResponse> {
  const aid = encodeURIComponent(advisorId);
  const url = `${API_BASE_URL}/api/v1/advisors/${aid}/tenants/portfolio`;
  const res = await fetch(url, {
    headers: {
      "x-api-key": API_KEY,
      "x-advisor-id": advisorId,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Advisor portfolio failed: ${res.status}`);
  }
  return res.json() as Promise<AdvisorPortfolioResponse>;
}

export async function fetchAdvisorPortfolioExportBlob(
  advisorId: string,
  format: "json" | "csv"
): Promise<Blob> {
  const aid = encodeURIComponent(advisorId);
  const url = `${API_BASE_URL}/api/v1/advisors/${aid}/tenants/portfolio-export?format=${format}`;
  const res = await fetch(url, {
    headers: {
      "x-api-key": API_KEY,
      "x-advisor-id": advisorId,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Advisor export failed: ${res.status}`);
  }
  return res.blob();
}

export interface AdvisorClientGovernanceSnapshotDto {
  advisor_id: string;
  client_tenant_id: string;
  generated_at_utc: string;
  client_info: {
    tenant_id: string;
    display_name: string;
    industry?: string | null;
    country?: string | null;
    tenant_kind?: string | null;
    registry_nis2_scope?: string | null;
    registry_ai_act_scope?: string | null;
  };
  setup_status: {
    guided_setup_completed_steps: number;
    guided_setup_total_steps: number;
    ai_governance_wizard_progress_steps: number[];
    ai_governance_wizard_steps_total: number;
    ai_governance_wizard_marked_steps: number[];
  };
  framework_scope: {
    active_frameworks: string[];
    compliance_scopes: string[];
  };
  ai_systems_summary: {
    total_count: number;
    high_risk_count: number;
    nis2_critical_count: number;
    by_risk_level: Record<string, number>;
    ki_register_registered: number;
    ki_register_planned: number;
    ki_register_partial: number;
    ki_register_unknown: number;
    advisor_attention_items: number;
  };
  kpi_summary: {
    high_risk_systems_in_scope: number;
    systems_with_kpi_values: number;
    critical_kpi_system_rows: number;
    aggregate_trends_non_flat: number;
  };
  cross_reg_summary: {
    framework_key: string;
    name: string;
    coverage_percent: number;
    gap_count: number;
    total_requirements: number;
  }[];
  gap_assist: {
    regulatory_gap_items_count: number;
    llm_gap_suggestions_count: number | null;
  };
  reports_summary: {
    reports_total: number;
    last_report_id: string | null;
    last_report_created_at: string | null;
    last_report_audience: string | null;
    last_report_title: string | null;
  };
  readiness?: ReadinessScoreResponseDto | null;
  /** OAMI (90 Tage), synthetisch in Demo – Post-Market / NIS2-Gespräch ohne PII. */
  operational_ai_monitoring?: {
    index_90d: number | null;
    level: string | null;
    has_runtime_data: boolean;
    systems_scored: number;
    narrative_de: string;
    drivers_de: string[];
    safety_related_runtime_incidents_90d?: number;
    availability_runtime_incidents_90d?: number;
    operational_subtype_hint_de?: string | null;
  } | null;
  governance_maturity_advisor_brief?: AdvisorGovernanceMaturityBriefDto | null;
}

export async function fetchAdvisorClientGovernanceSnapshot(
  advisorId: string,
  clientTenantId: string,
): Promise<AdvisorClientGovernanceSnapshotDto> {
  const aid = encodeURIComponent(advisorId);
  const tid = encodeURIComponent(clientTenantId);
  const url = `${API_BASE_URL}/api/v1/advisors/${aid}/tenants/${tid}/governance-snapshot`;
  const res = await fetch(url, {
    headers: {
      "x-api-key": API_KEY,
      "x-advisor-id": advisorId,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    if (res.status === 403) {
      throw new Error(
        "Governance-Snapshot nicht verfügbar (HTTP 403). Prüfen Sie API-Key, Advisor-Zuordnung oder Demo-Schreibrechte.",
      );
    }
    throw new Error(`Governance snapshot failed: ${res.status}`);
  }
  return res.json() as Promise<AdvisorClientGovernanceSnapshotDto>;
}

export async function postAdvisorGovernanceSnapshotMarkdown(
  advisorId: string,
  clientTenantId: string,
): Promise<{ markdown: string; provider: string; model_id: string }> {
  const aid = encodeURIComponent(advisorId);
  const tid = encodeURIComponent(clientTenantId);
  const url = `${API_BASE_URL}/api/v1/advisors/${aid}/tenants/${tid}/governance-snapshot-report`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "x-api-key": API_KEY,
      "x-advisor-id": advisorId,
      "Content-Type": "application/json",
    },
    body: "{}",
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Governance snapshot report failed: ${res.status}`);
  }
  return res.json() as Promise<{ markdown: string; provider: string; model_id: string }>;
}

/** Incident-Drilldown (Advisor → verknüpfter Mandant), JSON. */
export async function fetchAdvisorTenantIncidentDrilldown(
  advisorId: string,
  clientTenantId: string,
  windowDays = 90,
): Promise<TenantIncidentDrilldownOutDto> {
  const aid = encodeURIComponent(advisorId);
  const tid = encodeURIComponent(clientTenantId);
  const url = `${API_BASE_URL}/api/v1/advisors/${aid}/tenants/${tid}/incident-drilldown?window_days=${windowDays}`;
  const res = await fetch(url, {
    headers: {
      "x-api-key": API_KEY,
      "x-advisor-id": advisorId,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Incident drilldown failed: ${res.status}`);
  }
  return res.json() as Promise<TenantIncidentDrilldownOutDto>;
}

/** Incident-Drilldown als CSV-Blob (UTF-8). */
export async function fetchAdvisorTenantIncidentDrilldownCsvBlob(
  advisorId: string,
  clientTenantId: string,
  windowDays = 90,
): Promise<Blob> {
  const aid = encodeURIComponent(advisorId);
  const tid = encodeURIComponent(clientTenantId);
  const url = `${API_BASE_URL}/api/v1/advisors/${aid}/tenants/${tid}/incident-drilldown?window_days=${windowDays}&format=csv`;
  const res = await fetch(url, {
    headers: {
      "x-api-key": API_KEY,
      "x-advisor-id": advisorId,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Incident drilldown CSV failed: ${res.status}`);
  }
  return res.blob();
}

export interface AdvisorBoardReportListRowDto {
  tenant_id: string;
  tenant_display_name: string | null;
  report_id: string;
  title: string;
  audience_type: string;
  created_at: string;
}

export interface AdvisorBoardReportsPortfolioResponseDto {
  advisor_id: string;
  reports: AdvisorBoardReportListRowDto[];
}

export async function fetchAdvisorPortfolioBoardReports(
  advisorId: string,
  limitPerTenant = 30,
): Promise<AdvisorBoardReportsPortfolioResponseDto> {
  const aid = encodeURIComponent(advisorId);
  const url = `${API_BASE_URL}/api/v1/advisors/${aid}/tenants/board-reports?limit_per_tenant=${encodeURIComponent(String(limitPerTenant))}`;
  const res = await fetch(url, {
    headers: {
      "x-api-key": API_KEY,
      "x-advisor-id": advisorId,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Advisor board reports failed: ${res.status}`);
  }
  return res.json() as Promise<AdvisorBoardReportsPortfolioResponseDto>;
}

export async function fetchAdvisorBoardReportDetail(
  advisorId: string,
  tenantId: string,
  reportId: string,
): Promise<AiComplianceBoardReportDetailDto> {
  const aid = encodeURIComponent(advisorId);
  const tid = encodeURIComponent(tenantId);
  const rid = encodeURIComponent(reportId);
  const url = `${API_BASE_URL}/api/v1/advisors/${aid}/tenants/${tid}/board/ai-compliance-reports/${rid}`;
  const res = await fetch(url, {
    headers: {
      "x-api-key": API_KEY,
      "x-advisor-id": advisorId,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Advisor board report detail failed: ${res.status}`);
  }
  return res.json() as Promise<AiComplianceBoardReportDetailDto>;
}

/** Same-origin Proxy: `/api/advisor/tenant-report` (serverseitig API-Key, optional COMPLIANCEHUB_ADVISOR_ID). */
export function getAdvisorTenantReportUrl(
  tenantId: string,
  format: "json" | "markdown",
  advisorId: string = ADVISOR_ID_FROM_ENV,
): string {
  const params = new URLSearchParams({
    tenantId,
    format,
    advisorId,
  });
  return `/api/advisor/tenant-report?${params.toString()}`;
}

// ─── Demo-Tenant-Seeding (nur Pilot/Demo; Proxy nutzt COMPLIANCEHUB_DEMO_SEED_API_KEY) ─

export interface DemoTenantTemplateDto {
  key: string;
  name: string;
  description: string;
  industry: string;
  segment: string;
  country: string;
  nis2_scope: boolean;
  ai_act_high_risk_focus: boolean;
}

export interface DemoSeedResponseDto {
  template_key: string;
  tenant_id: string;
  ai_systems_count: number;
  governance_actions_count: number;
  evidence_files_count: number;
  nis2_kpi_rows_count: number;
  policy_rows_count: number;
  classifications_count: number;
  advisor_linked: boolean;
}

export async function fetchDemoTenantTemplates(): Promise<DemoTenantTemplateDto[]> {
  const res = await fetch("/api/demo/tenant-templates", { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Demo templates failed: ${res.status}`);
  }
  return res.json() as Promise<DemoTenantTemplateDto[]>;
}

export async function postDemoTenantSeed(payload: {
  template_key: string;
  tenant_id: string;
  advisor_id?: string | null;
}): Promise<DemoSeedResponseDto> {
  const res = await fetch("/api/demo/seed", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!res.ok) {
    const err = (await res.json().catch(() => ({}))) as { error?: string };
    throw new Error(err.error || `Demo seed failed: ${res.status}`);
  }
  return res.json() as Promise<DemoSeedResponseDto>;
}

// ─── Tenant-Nutzungsmetriken (Pilot / Telemetrie) ─────────────────────────────

export interface TenantUsageMetrics {
  tenant_id: string;
  last_active_at: string | null;
  board_views_last_30d: number;
  advisor_views_last_30d: number;
  evidence_uploads_last_30d: number;
  actions_created_last_30d: number;
}

export async function fetchTenantUsageMetrics(
  tenantId: string = TENANT_ID,
): Promise<TenantUsageMetrics> {
  const tid = encodeURIComponent(tenantId);
  return tenantApiFetch(`/api/v1/tenants/${tid}/usage-metrics`, tenantId);
}

/** Same-origin Proxy: nutzt serverseitigen API-Key und Advisor-Header. */
export async function fetchAdvisorTenantUsageMetrics(
  advisorId: string,
  tenantId: string,
): Promise<TenantUsageMetrics> {
  const params = new URLSearchParams({ advisorId, tenantId });
  const res = await fetch(`/api/advisor/tenant-usage-metrics?${params.toString()}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { error?: string };
    throw new Error(body.error || `Usage metrics failed: ${res.status}`);
  }
  return res.json() as Promise<TenantUsageMetrics>;
}

// ─── Mandanten-API-Keys (Pilot / ERP / ETL) ───────────────────────────────────

export interface TenantApiKeyReadDto {
  id: string;
  name: string;
  key_last4: string;
  created_at: string;
  active: boolean;
}

export interface TenantApiKeyCreatedDto extends TenantApiKeyReadDto {
  plain_key: string;
}

export async function fetchTenantApiKeys(tenantId: string): Promise<TenantApiKeyReadDto[]> {
  return tenantApiFetch(
    `/api/v1/tenants/${encodeURIComponent(tenantId)}/api-keys`,
    tenantId,
  );
}

export async function createTenantApiKey(
  tenantId: string,
  name: string,
): Promise<TenantApiKeyCreatedDto> {
  return tenantApiFetch(
    `/api/v1/tenants/${encodeURIComponent(tenantId)}/api-keys`,
    tenantId,
    {
      method: "POST",
      body: JSON.stringify({ name }),
    },
  );
}

export async function revokeTenantApiKey(tenantId: string, keyId: string): Promise<void> {
  const url = `${API_BASE_URL}/api/v1/tenants/${encodeURIComponent(tenantId)}/api-keys/${encodeURIComponent(keyId)}`;
  const res = await fetch(url, {
    method: "DELETE",
    headers: {
      "x-api-key": API_KEY,
      "x-tenant-id": tenantId,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`API-Key konnte nicht deaktiviert werden (${res.status})`);
  }
}

// ─── Cross-Regulation / Regelwerksgraph ──────────────────────────────────────

export interface CrossRegFrameworkSummaryDto {
  framework_key: string;
  name: string;
  subtitle: string;
  total_requirements: number;
  covered_requirements: number;
  gap_count: number;
  coverage_percent: number;
  partial_count: number;
  planned_only_count: number;
}

export interface CrossRegulationSummaryResponseDto {
  tenant_id: string;
  frameworks: CrossRegFrameworkSummaryDto[];
}

export interface RegulatoryRequirementRowDto {
  id: number;
  framework_key: string;
  framework_name: string;
  code: string;
  title: string;
  description: string | null;
  requirement_type: string;
  criticality: string;
  coverage_status: string;
  linked_control_count: number;
  primary_control_names: string[];
  related_framework_keys: string[];
}

export interface RegulatoryControlRowDto {
  id: string;
  name: string;
  description: string | null;
  control_type: string;
  owner_role: string | null;
  status: string;
  requirement_count: number;
  framework_count: number;
  framework_keys: string[];
}

export interface RequirementControlLinkDetailDto {
  link_id: number;
  control_id: string;
  control_name: string;
  coverage_level: string;
  control_status: string;
  owner_role: string | null;
  ai_system_ids: string[];
  policy_ids: string[];
  action_ids: string[];
}

export interface RequirementControlsDetailResponseDto {
  requirement: RegulatoryRequirementRowDto;
  links: RequirementControlLinkDetailDto[];
}

export interface AISystemRegulatoryHintDto {
  requirement_id: number;
  code: string;
  title: string;
  framework_key: string;
  via_control_name: string;
}

export async function fetchCrossRegulationSummary(
  tenantId: string,
): Promise<CrossRegulationSummaryResponseDto> {
  const tid = encodeURIComponent(tenantId);
  return tenantApiFetch(`/api/v1/tenants/${tid}/compliance/cross-regulation/summary`, tenantId);
}

export async function fetchRegulatoryRequirements(
  tenantId: string,
  framework?: string | null,
): Promise<RegulatoryRequirementRowDto[]> {
  const tid = encodeURIComponent(tenantId);
  const q = framework ? `?framework=${encodeURIComponent(framework)}` : "";
  return tenantApiFetch(`/api/v1/tenants/${tid}/compliance/regulatory-requirements${q}`, tenantId);
}

export async function fetchRegulatoryControls(tenantId: string): Promise<RegulatoryControlRowDto[]> {
  const tid = encodeURIComponent(tenantId);
  return tenantApiFetch(`/api/v1/tenants/${tid}/compliance/regulatory-controls`, tenantId);
}

export async function fetchRequirementControlsDetail(
  tenantId: string,
  requirementId: number,
): Promise<RequirementControlsDetailResponseDto> {
  const tid = encodeURIComponent(tenantId);
  const rid = encodeURIComponent(String(requirementId));
  return tenantApiFetch(
    `/api/v1/tenants/${tid}/compliance/regulatory-requirements/${rid}/controls`,
    tenantId,
  );
}

export async function fetchAiSystemRegulatoryContext(
  tenantId: string,
  aiSystemId: string,
): Promise<AISystemRegulatoryHintDto[]> {
  const tid = encodeURIComponent(tenantId);
  const sid = encodeURIComponent(aiSystemId);
  return tenantApiFetch(`/api/v1/tenants/${tid}/ai-systems/${sid}/regulatory-context`, tenantId);
}

export interface CrossRegLlmGapSuggestionDto {
  requirement_ids: number[];
  frameworks: string[];
  recommendation_type: string;
  suggested_control_name: string;
  suggested_control_description: string;
  rationale: string;
  priority: string;
  suggested_owner_role: string;
  suggested_actions: string[];
}

export interface CrossRegLlmGapAssistantResponseDto {
  tenant_id: string;
  suggestions: CrossRegLlmGapSuggestionDto[];
  gap_count_used: number;
}

export async function postCrossRegulationLlmGapAssistant(
  tenantId: string,
  body: { focus_frameworks?: string[] | null; max_suggestions?: number },
): Promise<CrossRegLlmGapAssistantResponseDto> {
  const tid = encodeURIComponent(tenantId);
  return tenantApiFetch(
    `/api/v1/tenants/${tid}/compliance/cross-regulation/llm-gap-assistant`,
    tenantId,
    {
      method: "POST",
      body: JSON.stringify({
        focus_frameworks: body.focus_frameworks ?? null,
        max_suggestions: body.max_suggestions ?? 8,
      }),
    },
  );
}

export type AiComplianceBoardReportAudience = "board" | "management" | "advisor_client";

export interface FrameworkCoverageSnapshotDto {
  framework_key: string;
  name: string;
  coverage_percent: number;
  total_requirements: number;
  covered_requirements: number;
  gap_count: number;
  partial_count: number;
  planned_only_count: number;
}

export interface AiComplianceBoardReportCreateBody {
  audience_type: AiComplianceBoardReportAudience;
  focus_frameworks?: string[] | null;
  include_ai_act_only?: boolean;
  language?: "de";
}

export interface AiComplianceBoardReportCreateResponseDto {
  report_id: string;
  title: string;
  rendered_markdown: string;
  coverage_snapshot: FrameworkCoverageSnapshotDto[];
  created_at: string;
  audience_type: string;
}

export interface AiComplianceBoardReportListItemDto {
  id: string;
  title: string;
  audience_type: string;
  created_at: string;
}

export interface AiComplianceBoardReportDetailDto {
  id: string;
  tenant_id: string;
  title: string;
  audience_type: string;
  created_at: string;
  rendered_markdown: string;
  raw_payload: Record<string, unknown>;
}

export async function createAiComplianceBoardReport(
  tenantId: string,
  body: AiComplianceBoardReportCreateBody,
): Promise<AiComplianceBoardReportCreateResponseDto> {
  const tid = encodeURIComponent(tenantId);
  return tenantApiFetch(
    `/api/v1/tenants/${tid}/board/ai-compliance-report`,
    tenantId,
    {
      method: "POST",
      body: JSON.stringify({
        audience_type: body.audience_type,
        focus_frameworks: body.focus_frameworks ?? null,
        include_ai_act_only: body.include_ai_act_only ?? false,
        language: body.language ?? "de",
      }),
    },
  );
}

export async function fetchAiComplianceBoardReports(
  tenantId: string,
): Promise<AiComplianceBoardReportListItemDto[]> {
  const tid = encodeURIComponent(tenantId);
  return tenantApiFetch(`/api/v1/tenants/${tid}/board/ai-compliance-reports`, tenantId);
}

export async function fetchAiComplianceBoardReportDetail(
  tenantId: string,
  reportId: string,
): Promise<AiComplianceBoardReportDetailDto> {
  const tid = encodeURIComponent(tenantId);
  const rid = encodeURIComponent(reportId);
  return tenantApiFetch(
    `/api/v1/tenants/${tid}/board/ai-compliance-reports/${rid}`,
    tenantId,
  );
}

// ─── AI-KPI / KRI (High-Risk-Monitoring, EU AI Act / ISO 42001) ───

export interface AiKpiDefinitionDto {
  id: string;
  key: string;
  name: string;
  description: string;
  category: string;
  unit: string;
  recommended_direction: "up" | "down";
  framework_tags: string[];
}

export interface AiSystemKpiValueDto {
  id: string;
  period_start: string;
  period_end: string;
  value: number;
  source: string;
  comment?: string | null;
}

export interface AiSystemKpiSeriesDto {
  definition: AiKpiDefinitionDto;
  periods: AiSystemKpiValueDto[];
  trend: "up" | "down" | "flat";
  latest_status: "ok" | "red";
}

export interface AiSystemKpisListResponseDto {
  ai_system_id: string;
  series: AiSystemKpiSeriesDto[];
}

export interface AiKpiPerKpiAggregateDto {
  kpi_key: string;
  name: string;
  unit: string;
  category: string;
  avg_latest: number | null;
  min_latest: number | null;
  max_latest: number | null;
  trend: "up" | "down" | "flat";
  systems_with_data: number;
}

export interface AiSystemCriticalKpiDto {
  kpi_key: string;
  name: string;
  value: number;
  unit: string;
}

export interface AiSystemCriticalRowDto {
  ai_system_id: string;
  ai_system_name: string;
  risk_level: string;
  critical_kpis: AiSystemCriticalKpiDto[];
}

export interface AiKpiSummaryResponseDto {
  per_kpi: AiKpiPerKpiAggregateDto[];
  per_system_critical: AiSystemCriticalRowDto[];
  high_risk_system_count: number;
}

export async function fetchTenantAiSystemKpis(
  tenantId: string,
  systemId: string,
): Promise<AiSystemKpisListResponseDto> {
  const tid = encodeURIComponent(tenantId);
  const sid = encodeURIComponent(systemId);
  return tenantApiFetch(`/api/v1/tenants/${tid}/ai-systems/${sid}/kpis`, tenantId);
}

export async function postTenantAiSystemKpi(
  tenantId: string,
  systemId: string,
  body: {
    kpi_definition_id: string;
    period_start: string;
    period_end: string;
    value: number;
    source?: "manual" | "api" | "import";
    comment?: string | null;
  },
): Promise<unknown> {
  const tid = encodeURIComponent(tenantId);
  const sid = encodeURIComponent(systemId);
  return tenantApiFetch(`/api/v1/tenants/${tid}/ai-systems/${sid}/kpis`, tenantId, {
    method: "POST",
    body: JSON.stringify({
      kpi_definition_id: body.kpi_definition_id,
      period_start: body.period_start,
      period_end: body.period_end,
      value: body.value,
      source: body.source ?? "manual",
      comment: body.comment ?? null,
    }),
  });
}

export async function fetchTenantAiKpiSummary(
  tenantId: string,
  params?: { framework_key?: string; criticality?: string },
): Promise<AiKpiSummaryResponseDto> {
  const tid = encodeURIComponent(tenantId);
  const q = new URLSearchParams();
  if (params?.framework_key) q.set("framework_key", params.framework_key);
  if (params?.criticality) q.set("criticality", params.criticality);
  const qs = q.toString();
  const path =
    qs.length > 0
      ? `/api/v1/tenants/${tid}/ai-kpis/summary?${qs}`
      : `/api/v1/tenants/${tid}/ai-kpis/summary`;
  return tenantApiFetch(path, tenantId);
}

export async function fetchTenantReadinessScore(tenantId: string): Promise<ReadinessScoreResponseDto> {
  const tid = encodeURIComponent(tenantId);
  return tenantApiFetch(`/api/v1/tenants/${tid}/readiness-score`, tenantId);
}

export async function postTenantReadinessScoreExplain(
  tenantId: string,
): Promise<ReadinessScoreExplainResponseDto> {
  const tid = encodeURIComponent(tenantId);
  return tenantApiFetch(`/api/v1/tenants/${tid}/readiness-score/explain`, tenantId, {
    method: "POST",
    body: "{}",
  });
}

export async function fetchAdvisorTenantReadinessScore(
  advisorId: string,
  clientTenantId: string,
): Promise<ReadinessScoreResponseDto> {
  const aid = encodeURIComponent(advisorId);
  const tid = encodeURIComponent(clientTenantId);
  const url = `${API_BASE_URL}/api/v1/advisors/${aid}/tenants/${tid}/readiness-score`;
  const res = await fetch(url, {
    headers: {
      "x-api-key": API_KEY,
      "x-advisor-id": advisorId,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Advisor readiness score failed: ${res.status}`);
  }
  return res.json() as Promise<ReadinessScoreResponseDto>;
}

// ---------------------------------------------------------------------------
// Internal: Advisor Metrics
// ---------------------------------------------------------------------------

export interface AdvisorDailyMetricsDto {
  date: string;
  tenant_id: string;
  total_queries: number;
  retrieval_mode_bm25: number;
  retrieval_mode_hybrid: number;
  confidence_high: number;
  confidence_medium: number;
  confidence_low: number;
  agent_answered: number;
  agent_escalated: number;
}

export interface AdvisorMetricsDto {
  tenant_id: string | null;
  from_date: string | null;
  to_date: string | null;
  total_queries: number;
  retrieval_mode_distribution: Record<string, number>;
  confidence_distribution: Record<string, number>;
  escalation_rate: number | null;
  agent_decision_distribution: Record<string, number>;
  daily: AdvisorDailyMetricsDto[];
}

export async function fetchAdvisorMetrics(
  params?: { tenant_id?: string; from?: string; to?: string },
): Promise<AdvisorMetricsDto> {
  const qs = new URLSearchParams();
  if (params?.tenant_id) qs.set("tenant_id", params.tenant_id);
  if (params?.from) qs.set("from", params.from);
  if (params?.to) qs.set("to", params.to);
  const url = `${API_BASE_URL}/api/internal/advisor/metrics${qs.toString() ? `?${qs}` : ""}`;
  const res = await fetch(url, {
    headers: tenantRequestHeaders(TENANT_ID),
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Advisor metrics failed: ${res.status}`);
  }
  return res.json() as Promise<AdvisorMetricsDto>;
}

export type ControlCenterSeverityDto = "critical" | "warning" | "info";
export type ControlCenterStatusDto = "open" | "due_soon" | "overdue" | "blocked" | "ok";
export type ControlCenterSectionDto =
  | "audit"
  | "incidents_reporting"
  | "regulatory_deadlines"
  | "register_export_obligations"
  | "board_readiness";

export interface EnterpriseControlCenterItemDto {
  section: ControlCenterSectionDto;
  severity: ControlCenterSeverityDto;
  status: ControlCenterStatusDto;
  title: string;
  summary_de: string;
  due_at: string | null;
  tenant_id: string;
  source_type: string;
  source_id: string;
  action_label: string;
  action_href: string;
}

export interface EnterpriseControlCenterSectionGroupDto {
  section: ControlCenterSectionDto;
  label_de: string;
  items: EnterpriseControlCenterItemDto[];
}

export interface EnterpriseControlCenterResponseDto {
  tenant_id: string;
  generated_at_utc: string;
  summary_counts: {
    critical: number;
    warning: number;
    info: number;
    total_open: number;
  };
  grouped_sections: EnterpriseControlCenterSectionGroupDto[];
  top_urgent_items: EnterpriseControlCenterItemDto[];
  markdown_de?: string | null;
}

export async function fetchEnterpriseControlCenter(
  tenantId: string,
  includeMarkdown = false,
): Promise<EnterpriseControlCenterResponseDto> {
  const qs = includeMarkdown ? "?include_markdown=true" : "";
  return tenantApiFetch(
    `/api/internal/enterprise/control-center${qs}`,
    tenantId,
  ) as Promise<EnterpriseControlCenterResponseDto>;
}

export type PreparationPackFocusDto = "audit" | "authority" | "mixed";

export interface AuthorityAuditPreparationPackSectionDto {
  title_de: string;
  summary_de: string;
  evidence_items: string[];
  missing_items: string[];
  due_items: string[];
}

export interface AuthorityAuditPreparationPackResponseDto {
  tenant_id: string;
  generated_at_utc: string;
  focus: PreparationPackFocusDto;
  source_sections: string[];
  section_a_executive_posture: AuthorityAuditPreparationPackSectionDto;
  section_b_open_critical_missing_evidence: AuthorityAuditPreparationPackSectionDto;
  section_c_audit_trail_readiness: AuthorityAuditPreparationPackSectionDto;
  section_d_nis2_incident_deadline_status: AuthorityAuditPreparationPackSectionDto;
  section_e_ai_act_register_authority_status: AuthorityAuditPreparationPackSectionDto;
  section_f_recommended_next_preparation_actions: AuthorityAuditPreparationPackSectionDto;
  section_g_integration_blueprint_posture: AuthorityAuditPreparationPackSectionDto;
  markdown_de: string;
}

export async function fetchAuthorityAuditPreparationPack(
  tenantId: string,
  focus: PreparationPackFocusDto = "mixed",
): Promise<AuthorityAuditPreparationPackResponseDto> {
  const qs = new URLSearchParams({ focus });
  return tenantApiFetch(
    `/api/internal/enterprise/authority-audit-pack?${qs.toString()}`,
    tenantId,
  ) as Promise<AuthorityAuditPreparationPackResponseDto>;
}

export type IntegrationBlueprintSourceSystemTypeDto =
  | "sap_btp"
  | "sap_s4hana"
  | "datev"
  | "ms_dynamics"
  | "generic_api";
export type IntegrationBlueprintEvidenceDomainDto =
  | "invoice"
  | "approval"
  | "access"
  | "vendor"
  | "ai_inventory"
  | "policy_artifact"
  | "workflow_evidence"
  | "tax_export_context";
export type IntegrationBlueprintStatusDto =
  | "planned"
  | "designing"
  | "blocked"
  | "ready_for_build";
export type IntegrationBlueprintReadinessPostureDto =
  | "integration_ready"
  | "preparing"
  | "blocked";

export interface EnterpriseIntegrationBlueprintResponseDto {
  tenant_id: string;
  generated_at_utc: string;
  readiness_status: IntegrationBlueprintReadinessPostureDto;
  blueprint_rows: {
    blueprint_id: string;
    tenant_id: string;
    source_system_type: IntegrationBlueprintSourceSystemTypeDto;
    evidence_domains: IntegrationBlueprintEvidenceDomainDto[];
    onboarding_readiness_ref: string | null;
    security_prerequisites: string[];
    data_owner: string | null;
    technical_owner: string | null;
    integration_status: IntegrationBlueprintStatusDto;
    blockers: string[];
    notes: string | null;
  }[];
  blockers: string[];
  top_enterprise_integration_candidates: {
    blueprint_id: string;
    source_system_type: IntegrationBlueprintSourceSystemTypeDto;
    score: number;
    recommendation_de: string;
    unlocked_evidence_domains: IntegrationBlueprintEvidenceDomainDto[];
    blockers: string[];
  }[];
  markdown_de?: string | null;
}

export async function fetchEnterpriseIntegrationBlueprints(
  tenantId: string,
  includeMarkdown = false,
): Promise<EnterpriseIntegrationBlueprintResponseDto> {
  const qs = includeMarkdown ? "?include_markdown=true" : "";
  return tenantApiFetch(
    `/api/internal/enterprise/integration-blueprints${qs}`,
    tenantId,
  ) as Promise<EnterpriseIntegrationBlueprintResponseDto>;
}

export type ConnectorCandidatePriorityDto = "high" | "medium" | "low" | "not_now";
export type ConnectorComplexityBandDto = "low" | "medium" | "high";

export interface EnterpriseConnectorCandidateRowDto {
  tenant_id: string;
  connector_type: IntegrationBlueprintSourceSystemTypeDto;
  readiness_score: number;
  blocker_score: number;
  strategic_value_score: number;
  compliance_impact_score: number;
  estimated_implementation_complexity: number;
  complexity_band: ConnectorComplexityBandDto;
  recommended_priority: ConnectorCandidatePriorityDto;
  rationale_summary_de: string;
  rationale_factors_de: string[];
  score_total: number;
}

export interface EnterpriseConnectorCandidatesResponseDto {
  tenant_id: string;
  generated_at_utc: string;
  scoring_weights: {
    readiness_weight: number;
    blocker_weight: number;
    strategic_value_weight: number;
    compliance_impact_weight: number;
  };
  candidate_rows: EnterpriseConnectorCandidateRowDto[];
  top_priorities: EnterpriseConnectorCandidateRowDto[];
  grouped_priorities_by_connector_type: Record<string, EnterpriseConnectorCandidateRowDto[]>;
  markdown_de?: string | null;
}

export async function fetchEnterpriseConnectorCandidates(
  tenantId: string,
  includeMarkdown = false,
): Promise<EnterpriseConnectorCandidatesResponseDto> {
  const qs = includeMarkdown ? "?include_markdown=true" : "";
  return tenantApiFetch(
    `/api/internal/enterprise/connector-candidates${qs}`,
    tenantId,
  ) as Promise<EnterpriseConnectorCandidatesResponseDto>;
}

export type IdentityProviderTypeDto =
  | "azure_ad"
  | "saml_generic"
  | "sap_ias"
  | "google_workspace"
  | "okta"
  | "other";
export type ReadinessStatusDto = "not_started" | "planned" | "configured" | "validated";

export interface EnterpriseOnboardingReadinessDto {
  tenant_id: string;
  updated_at_utc: string;
  updated_by: string;
  enterprise_name: string | null;
  tenant_structure: {
    entity_code: string;
    name: string;
    entity_type: string;
    parent_entity_code: string | null;
  }[];
  advisor_visibility_enabled: boolean;
  sso_readiness: {
    provider_type: IdentityProviderTypeDto;
    onboarding_status: ReadinessStatusDto;
    role_mapping_status: ReadinessStatusDto;
    identity_domain: string | null;
    metadata_hint: string | null;
    role_mapping_rules: { external_group_or_claim: string; mapped_role: string; notes: string | null }[];
  };
  integration_readiness: {
    target_type: string;
    readiness_status: string;
    owner: string | null;
    notes: string | null;
    blocker: string | null;
    evidence_ref: string | null;
  }[];
  rollout_notes: string | null;
  blockers: { key: string; title_de: string; severity: string }[];
}

export async function fetchEnterpriseOnboardingReadiness(
  tenantId: string,
): Promise<EnterpriseOnboardingReadinessDto> {
  return tenantApiFetch(
    "/api/internal/enterprise/onboarding-readiness",
    tenantId,
  ) as Promise<EnterpriseOnboardingReadinessDto>;
}
