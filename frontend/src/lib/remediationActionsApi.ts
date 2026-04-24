export interface RemediationSummaryDto {
  open_actions: number;
  backlog_actions: number;
  overdue_actions: number;
  blocked_actions: number;
  due_this_week: number;
}

export interface RemediationLinkDto {
  entity_type: string;
  entity_id: string;
}

export interface RemediationActionListItemDto {
  id: string;
  title: string;
  status: string;
  priority: string;
  owner: string | null;
  due_at_utc: string | null;
  is_overdue: boolean;
  category: string;
  rule_key: string | null;
  updated_at_utc: string;
  links: RemediationLinkDto[];
}

export interface RemediationListResponseDto {
  items: RemediationActionListItemDto[];
  summary: RemediationSummaryDto;
}

export interface RemediationCommentDto {
  id: string;
  body: string;
  created_by: string | null;
  created_at_utc: string;
}

export interface RemediationStatusHistoryDto {
  id: string;
  from_status: string | null;
  to_status: string;
  changed_at_utc: string;
  changed_by: string | null;
  note: string | null;
}

export interface RemediationActionDetailDto {
  id: string;
  tenant_id: string;
  title: string;
  description: string | null;
  status: string;
  priority: string;
  owner: string | null;
  due_at_utc: string | null;
  is_overdue: boolean;
  category: string;
  rule_key: string | null;
  deferred_note: string | null;
  created_at_utc: string;
  updated_at_utc: string;
  created_by: string | null;
  links: RemediationLinkDto[];
  comments: RemediationCommentDto[];
  status_history: RemediationStatusHistoryDto[];
}

export interface RemediationGenerateResponseDto {
  created_count: number;
  rule_keys_touched: string[];
  evaluated_at_utc: string;
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

export async function fetchRemediationActions(
  tenantId: string,
  params: {
    status?: string;
    priority?: string;
    category?: string;
    rule_key?: string;
    framework_tag?: string;
    search?: string;
    sort?: "updated_desc" | "due_asc" | "due_desc" | "priority_desc";
    limit?: number;
  } = {},
): Promise<RemediationListResponseDto> {
  const qs = new URLSearchParams();
  if (params.status) qs.set("status", params.status);
  if (params.priority) qs.set("priority", params.priority);
  if (params.category) qs.set("category", params.category);
  if (params.rule_key) qs.set("rule_key", params.rule_key);
  if (params.framework_tag) qs.set("framework_tag", params.framework_tag);
  if (params.search?.trim()) qs.set("search", params.search.trim());
  if (params.sort) qs.set("sort", params.sort);
  if (params.limit != null) qs.set("limit", String(params.limit));
  const q = qs.toString();
  const base = apiBase().replace(/\/$/, "");
  const path = `/api/v1/governance/remediation-actions${q ? `?${q}` : ""}`;
  const res = await fetch(`${base}${path}`, { headers: headers(tenantId), cache: "no-store" });
  if (!res.ok) throw new Error(`Remediation API ${res.status}`);
  return (await res.json()) as RemediationListResponseDto;
}

export async function fetchRemediationActionDetail(
  tenantId: string,
  actionId: string,
): Promise<RemediationActionDetailDto> {
  const base = apiBase().replace(/\/$/, "");
  const res = await fetch(
    `${base}/api/v1/governance/remediation-actions/${encodeURIComponent(actionId)}`,
    { headers: headers(tenantId), cache: "no-store" },
  );
  if (!res.ok) throw new Error(`Remediation detail ${res.status}`);
  return (await res.json()) as RemediationActionDetailDto;
}

export async function generateRemediationActions(
  tenantId: string,
): Promise<RemediationGenerateResponseDto> {
  const base = apiBase().replace(/\/$/, "");
  const res = await fetch(`${base}/api/v1/governance/remediation-actions/generate`, {
    method: "POST",
    headers: headers(tenantId),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Remediation generate ${res.status}`);
  return (await res.json()) as RemediationGenerateResponseDto;
}

export async function postRemediationComment(
  tenantId: string,
  actionId: string,
  body: string,
): Promise<RemediationCommentDto> {
  const base = apiBase().replace(/\/$/, "");
  const res = await fetch(
    `${base}/api/v1/governance/remediation-actions/${encodeURIComponent(actionId)}/comments`,
    {
      method: "POST",
      headers: headers(tenantId),
      cache: "no-store",
      body: JSON.stringify({ body }),
    },
  );
  if (!res.ok) throw new Error(`Remediation comment ${res.status}`);
  return (await res.json()) as RemediationCommentDto;
}
