/**
 * EU AI Act Self-Assessment API client (FastAPI).
 *
 * Wiring: set NEXT_PUBLIC_AI_ACT_SELF_ASSESSMENT_PREFIX (default "/ai-act")
 * and NEXT_PUBLIC_AI_ACT_AUDIT_PREFIX (default "/audit") to match your mount,
 * e.g. "/api/v1/ai-act" if the router is included under /api/v1.
 */
import { tenantRequestHeaders } from "@/lib/api";

export function getComplianceHubApiBaseUrl(): string {
  return (
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    process.env.COMPLIANCEHUB_API_BASE_URL ||
    "http://localhost:8000"
  );
}

const SA_PREFIX = (
  process.env.NEXT_PUBLIC_AI_ACT_SELF_ASSESSMENT_PREFIX ?? "/ai-act"
).replace(/\/$/, "");

const AUDIT_PREFIX = (process.env.NEXT_PUBLIC_AI_ACT_AUDIT_PREFIX ?? "/audit").replace(
  /\/$/,
  "",
);

export type SelfAssessmentStatus = "draft" | "in_review" | "completed";

export interface SelfAssessmentListItem {
  session_id: string;
  status: SelfAssessmentStatus | string;
  ai_system_id?: string | null;
  ai_system_name?: string | null;
  schema_version?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  owner?: string | null;
  created_by?: string | null;
}

export interface SelfAssessmentSessionDetail extends SelfAssessmentListItem {
  updated_at?: string | null;
}

export interface SelfAssessmentClassification {
  risk_level?: string | null;
  rationale?: string | null;
  eu_ai_act_refs?: string[] | null;
  requires_manual_review?: boolean | null;
}

export interface SelfAssessmentAuditEvent {
  event_type?: string | null;
  type?: string | null;
  user?: string | null;
  actor?: string | null;
  user_id?: string | null;
  timestamp?: string | null;
  created_at?: string | null;
  details?: string | Record<string, unknown> | null;
  detail?: string | Record<string, unknown> | null;
}

export type SaApiOk<T> = { ok: true; data: T };
export type SaApiErr = { ok: false; status: number; message: string };
export type SaApiResult<T> = SaApiOk<T> | SaApiErr;

function saBase(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${SA_PREFIX}${p}`;
}

function auditBase(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${AUDIT_PREFIX}${p}`;
}

async function readErrorMessage(res: Response): Promise<string> {
  const raw = await res.text();
  try {
    const j = JSON.parse(raw) as { detail?: unknown };
    if (typeof j.detail === "string") {
      return j.detail;
    }
    if (Array.isArray(j.detail)) {
      return j.detail
        .map((e) => {
          if (e && typeof e === "object" && "msg" in e) {
            return String((e as { msg: unknown }).msg);
          }
          return JSON.stringify(e);
        })
        .join("; ");
    }
  } catch {
    // ignore
  }
  return raw.trim() || `HTTP ${res.status}`;
}

export async function tenantSaFetchJson<T>(
  tenantId: string,
  path: string,
  init?: RequestInit,
): Promise<SaApiResult<T>> {
  const url = `${getComplianceHubApiBaseUrl()}${path}`;
  let res: Response;
  try {
    res = await fetch(url, {
      ...init,
      headers: tenantRequestHeaders(tenantId, init?.headers, {
        json: init?.body != null || (init?.method ?? "GET").toUpperCase() !== "GET",
      }),
      cache: "no-store",
    });
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return { ok: false, status: 0, message: `Netzwerkfehler: ${msg}` };
  }

  try {
    if (res.status === 204) {
      return { ok: true, data: undefined as T };
    }
    if (!res.ok) {
      return { ok: false, status: res.status, message: await readErrorMessage(res) };
    }
    const ct = res.headers.get("content-type") ?? "";
    if (!ct.includes("application/json")) {
      const text = await res.text();
      return { ok: true, data: text as unknown as T };
    }
    return { ok: true, data: (await res.json()) as T };
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return {
      ok: false,
      status: res.status,
      message: `Antwortverarbeitung fehlgeschlagen: ${msg}`,
    };
  }
}

export function normalizeSessionId(row: Record<string, unknown>): string {
  const sid = row.session_id ?? row.id;
  return String(sid ?? "");
}

export function normalizeListResponse(body: unknown): SelfAssessmentListItem[] {
  if (Array.isArray(body)) {
    return body.map((row) => normalizeListItem(row as Record<string, unknown>));
  }
  if (body && typeof body === "object") {
    const o = body as Record<string, unknown>;
    const arr =
      (o.items as unknown) ??
      (o.self_assessments as unknown) ??
      (o.data as unknown) ??
      (o.results as unknown);
    if (Array.isArray(arr)) {
      return arr.map((row) => normalizeListItem(row as Record<string, unknown>));
    }
  }
  return [];
}

function normalizeListItem(row: Record<string, unknown>): SelfAssessmentListItem {
  return {
    session_id: normalizeSessionId(row),
    status: String(row.status ?? "draft"),
    ai_system_id: row.ai_system_id != null ? String(row.ai_system_id) : null,
    ai_system_name: row.ai_system_name != null ? String(row.ai_system_name) : null,
    schema_version: row.schema_version != null ? String(row.schema_version) : null,
    started_at: row.started_at != null ? String(row.started_at) : null,
    completed_at: row.completed_at != null ? String(row.completed_at) : null,
    owner: row.owner != null ? String(row.owner) : null,
    created_by: row.created_by != null ? String(row.created_by) : null,
  };
}

export function normalizeSessionDetail(body: unknown): SelfAssessmentSessionDetail | null {
  if (!body || typeof body !== "object") {
    return null;
  }
  const row = body as Record<string, unknown>;
  const id = normalizeSessionId(row);
  if (!id) {
    return null;
  }
  return { ...normalizeListItem(row), updated_at: row.updated_at != null ? String(row.updated_at) : null };
}

export function normalizeAnswersPayload(body: unknown): Record<string, unknown> {
  if (!body || typeof body !== "object") {
    return {};
  }
  const o = body as Record<string, unknown>;
  const inner = o.answers;
  if (inner && typeof inner === "object" && !Array.isArray(inner)) {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(inner as Record<string, unknown>)) {
      if (v && typeof v === "object" && !Array.isArray(v) && "value" in v) {
        out[k] = (v as { value: unknown }).value;
      } else {
        out[k] = v;
      }
    }
    return out;
  }
  // flat map of question_key -> value
  const skip = new Set(["session_id", "tenant_id", "status"]);
  const flat: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(o)) {
    if (!skip.has(k)) {
      flat[k] = v;
    }
  }
  return flat;
}

export function normalizeAuditEvents(body: unknown): SelfAssessmentAuditEvent[] {
  if (Array.isArray(body)) {
    return body as SelfAssessmentAuditEvent[];
  }
  if (body && typeof body === "object") {
    const o = body as Record<string, unknown>;
    const arr = (o.events as unknown) ?? (o.items as unknown);
    if (Array.isArray(arr)) {
      return arr as SelfAssessmentAuditEvent[];
    }
  }
  return [];
}

export function normalizeClassification(body: unknown): SelfAssessmentClassification | null {
  if (!body || typeof body !== "object") {
    return null;
  }
  const o = body as Record<string, unknown>;
  const refs = o.eu_ai_act_refs;
  return {
    risk_level: o.risk_level != null ? String(o.risk_level) : null,
    rationale: o.rationale != null ? String(o.rationale) : null,
    eu_ai_act_refs: Array.isArray(refs) ? refs.map(String) : null,
    requires_manual_review:
      typeof o.requires_manual_review === "boolean" ? o.requires_manual_review : null,
  };
}

export async function listSelfAssessments(
  tenantId: string,
): Promise<SaApiResult<SelfAssessmentListItem[]>> {
  const r = await tenantSaFetchJson<unknown>(tenantId, saBase("/self-assessments"));
  if (!r.ok) {
    return r;
  }
  return { ok: true, data: normalizeListResponse(r.data) };
}

export async function createSelfAssessment(
  tenantId: string,
  body: Record<string, unknown> = {},
): Promise<SaApiResult<{ session_id?: string; id?: string }>> {
  return tenantSaFetchJson(tenantId, saBase("/self-assessments"), {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getSelfAssessmentSession(
  tenantId: string,
  sessionId: string,
): Promise<SaApiResult<SelfAssessmentSessionDetail | null>> {
  const r = await tenantSaFetchJson<unknown>(
    tenantId,
    saBase(`/self-assessments/${encodeURIComponent(sessionId)}`),
  );
  if (!r.ok) {
    return r;
  }
  return { ok: true, data: normalizeSessionDetail(r.data) };
}

export async function patchSelfAssessmentSession(
  tenantId: string,
  sessionId: string,
  body: Record<string, unknown>,
): Promise<SaApiResult<SelfAssessmentSessionDetail | null>> {
  const r = await tenantSaFetchJson<unknown>(
    tenantId,
    saBase(`/self-assessments/${encodeURIComponent(sessionId)}`),
    { method: "PATCH", body: JSON.stringify(body) },
  );
  if (!r.ok) {
    return r;
  }
  return { ok: true, data: normalizeSessionDetail(r.data) };
}

export async function completeSelfAssessment(
  tenantId: string,
  sessionId: string,
): Promise<SaApiResult<unknown>> {
  return tenantSaFetchJson(
    tenantId,
    saBase(`/self-assessments/${encodeURIComponent(sessionId)}/complete`),
    { method: "POST", body: JSON.stringify({}) },
  );
}

export async function getSelfAssessmentAnswers(
  tenantId: string,
  sessionId: string,
): Promise<SaApiResult<Record<string, unknown>>> {
  const r = await tenantSaFetchJson<unknown>(
    tenantId,
    saBase(`/self-assessments/${encodeURIComponent(sessionId)}/answers`),
  );
  if (!r.ok) {
    return r;
  }
  return { ok: true, data: normalizeAnswersPayload(r.data) };
}

export async function putSelfAssessmentAnswer(
  tenantId: string,
  sessionId: string,
  questionKey: string,
  value: unknown,
): Promise<SaApiResult<unknown>> {
  return tenantSaFetchJson(
    tenantId,
    saBase(
      `/self-assessments/${encodeURIComponent(sessionId)}/answers/${encodeURIComponent(questionKey)}`,
    ),
    { method: "PUT", body: JSON.stringify({ value }) },
  );
}

export async function getSelfAssessmentClassification(
  tenantId: string,
  sessionId: string,
): Promise<SaApiResult<SelfAssessmentClassification | null>> {
  const r = await tenantSaFetchJson<unknown>(
    tenantId,
    saBase(`/self-assessments/${encodeURIComponent(sessionId)}/classification`),
  );
  if (!r.ok) {
    return r;
  }
  return { ok: true, data: normalizeClassification(r.data) };
}

export interface ExportSelfAssessmentResult {
  download_url?: string;
  url?: string;
  file_url?: string;
}

export async function exportSelfAssessment(
  tenantId: string,
  sessionId: string,
): Promise<SaApiResult<ExportSelfAssessmentResult>> {
  return tenantSaFetchJson(
    tenantId,
    saBase(`/self-assessments/${encodeURIComponent(sessionId)}/export`),
    { method: "POST", body: JSON.stringify({}) },
  );
}

export async function getSelfAssessmentAuditEvents(
  tenantId: string,
  sessionId: string,
): Promise<SaApiResult<SelfAssessmentAuditEvent[]>> {
  const r = await tenantSaFetchJson<unknown>(
    tenantId,
    auditBase(`/self-assessments/${encodeURIComponent(sessionId)}/events`),
  );
  if (!r.ok) {
    return r;
  }
  return { ok: true, data: normalizeAuditEvents(r.data) };
}

export function resolveExportDownloadUrl(payload: ExportSelfAssessmentResult): string | null {
  const u = payload.download_url ?? payload.url ?? payload.file_url;
  if (!u) {
    return null;
  }
  if (u.startsWith("http://") || u.startsWith("https://")) {
    return u;
  }
  const base = getComplianceHubApiBaseUrl().replace(/\/$/, "");
  return `${base}${u.startsWith("/") ? u : `/${u}`}`;
}
