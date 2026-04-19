export interface BoardMetricDto {
  metric_key: string;
  label: string;
  value: number;
  unit: string;
  traffic_light: "green" | "amber" | "red";
  trend_direction: "up" | "down" | "stable";
  trend_delta: number;
  narrative_de: string | null;
}

export interface BoardReportSummaryDto {
  report_id: string;
  period_key: string;
  period_type: string;
  generated_at_utc: string;
  headline_de: string;
  top_risk_areas: string[];
  metrics: BoardMetricDto[];
  resilience_summary_de: string;
}

export interface BoardActionDto {
  id: string;
  action_title: string;
  action_detail: string | null;
  owner: string | null;
  due_at: string | null;
  status: string;
  priority: string;
  source_type: string;
  source_id: string | null;
}

export interface BoardReportDetailDto {
  id: string;
  tenant_id: string;
  period_key: string;
  period_type: string;
  period_start: string;
  period_end: string;
  title: string;
  status: string;
  generated_at_utc: string;
  generated_by: string | null;
  summary: BoardReportSummaryDto;
  actions: BoardActionDto[];
  audit_trail: Array<Record<string, string>>;
}

export interface BoardReportListItemDto {
  id: string;
  tenant_id: string;
  period_key: string;
  period_type: string;
  title: string;
  status: string;
  generated_at_utc: string;
  generated_by: string | null;
}

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

function headers(tenantId: string): Record<string, string> {
  return { "x-api-key": apiKey(), "x-tenant-id": tenantId, "Content-Type": "application/json" };
}

async function getJson<T>(tenantId: string, path: string): Promise<T> {
  const base = apiBase().replace(/\/$/, "");
  const res = await fetch(`${base}${path}`, { headers: headers(tenantId), cache: "no-store" });
  if (!res.ok) throw new Error(`Board Reporting API ${res.status}`);
  return (await res.json()) as T;
}

export async function fetchBoardReports(tenantId: string): Promise<BoardReportListItemDto[]> {
  return getJson<BoardReportListItemDto[]>(tenantId, "/api/v1/governance/board-reports");
}

export async function generateBoardReport(tenantId: string, body: {
  period_key: string;
  period_type: "monthly" | "quarterly";
  period_start: string;
  period_end: string;
  title?: string;
}): Promise<BoardReportDetailDto> {
  const base = apiBase().replace(/\/$/, "");
  const res = await fetch(`${base}/api/v1/governance/board-reports/generate`, {
    method: "POST",
    headers: headers(tenantId),
    cache: "no-store",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Generate Board Report ${res.status}`);
  return (await res.json()) as BoardReportDetailDto;
}

export async function fetchBoardReport(tenantId: string, reportId: string): Promise<BoardReportDetailDto> {
  return getJson<BoardReportDetailDto>(
    tenantId,
    `/api/v1/governance/board-reports/${encodeURIComponent(reportId)}`,
  );
}
