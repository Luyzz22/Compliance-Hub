/**
 * Wave 28.2 – Pipedrive-Deals nur für qualifizierte Leads (siehe `pipedriveDealEligibility`).
 * HubSpot bleibt breiteres Kontakt-/Aktivitäts-System; Pipedrive = schmaler Pipeline-Pfad.
 */
import "server-only";

import { attachContactRollups, mergeLeadsWithOps } from "@/lib/leadInboxMerge";
import { readLeadOpsState } from "@/lib/leadOpsState";
import {
  buildLeadSyncPayloadV1,
  type LegacyInboundDelivery,
} from "@/lib/leadSyncPayload";
import { getMergedLeadAdminRow, readAllLeadRecordsMerged } from "@/lib/leadPersistence";
import { isLeadPipedriveDealEligible } from "@/lib/pipedriveDealEligibility";
import type { LeadSyncConnectorResult, LeadSyncPayloadV1 } from "@/lib/leadSyncTypes";

const PD_BASE = "https://api.pipedrive.com/v1";
const REQUEST_TIMEOUT_MS = 28_000;

const DEAL_TITLE_PREFIX = "CH-LID:";

export type LeadSyncPipedriveSyncResult = {
  system: "pipedrive";
  synced_at: string;
  person_id: string;
  org_id?: string;
  org_association:
    | "linked"
    | "skipped_weak_name"
    | "skipped_no_match"
    | "skipped_ambiguous"
    | "skipped_create_disabled";
  deal_id: string;
  deal_action: "created" | "updated";
  pipeline_id: number;
  stage_id: number;
};

type PdEnvelope<T> = {
  success?: boolean;
  data?: T;
  error?: string;
  error_info?: string;
};

function isWeakOrgName(name: string): boolean {
  const t = name.trim();
  if (t.length < 2) return true;
  return /^(n\/a|na|none|unknown|unbekannt|test|xxx|-+)$/i.test(t);
}

function classifyPipedriveRetryable(status: number, errMsg: string): boolean {
  const m = errMsg.toLowerCase();
  if (status === 429) return true;
  if (status >= 500) return true;
  if (status === 401) return false;
  if (status === 403) return false;
  if (status === 404 && m.includes("not found")) return false;
  if (status === 400) return false;
  if (status >= 400) return false;
  return true;
}

function formatPdError(status: number, parsed: PdEnvelope<unknown> | null, raw: string): string {
  const parts = [`http_${status}`];
  if (parsed?.error) parts.push(parsed.error);
  if (parsed?.error_info) parts.push(String(parsed.error_info).slice(0, 200));
  else if (raw) parts.push(raw.slice(0, 280));
  return parts.join(": ");
}

async function pdFetch(
  token: string,
  method: "GET" | "POST" | "PUT",
  path: string,
  opts?: { query?: Record<string, string>; body?: unknown },
): Promise<{ status: number; parsed: PdEnvelope<unknown> | null; raw: string }> {
  const url = new URL(`${PD_BASE}${path.startsWith("/") ? path : `/${path}`}`);
  url.searchParams.set("api_token", token);
  if (opts?.query) {
    for (const [k, v] of Object.entries(opts.query)) {
      if (v !== "") url.searchParams.set(k, v);
    }
  }
  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const init: RequestInit = {
      method,
      signal: controller.signal,
      headers: { "Content-Type": "application/json", Accept: "application/json" },
    };
    if (opts?.body !== undefined && method !== "GET") {
      init.body = JSON.stringify(opts.body);
    }
    const r = await fetch(url.toString(), init);
    const raw = await r.text();
    let parsed: PdEnvelope<unknown> | null = null;
    try {
      parsed = JSON.parse(raw) as PdEnvelope<unknown>;
    } catch {
      /* ignore */
    }
    return { status: r.status, parsed, raw };
  } finally {
    clearTimeout(t);
  }
}

function requirePdSuccess(
  r: { status: number; parsed: PdEnvelope<unknown> | null; raw: string },
  op: string,
): void {
  if (r.parsed?.success === true) return;
  const st = r.status >= 400 ? r.status : 400;
  throw { status: st, parsed: r.parsed, raw: r.raw, op };
}

async function resolveFreshPayload(snapshot: LeadSyncPayloadV1): Promise<LeadSyncPayloadV1 | null> {
  const row = await getMergedLeadAdminRow(snapshot.lead_id);
  if (!row) return null;
  const allRows = await readAllLeadRecordsMerged();
  const ops = await readLeadOpsState();
  const merged = mergeLeadsWithOps([row], ops);
  const inboxItem = attachContactRollups(merged, allRows, ops)[0];
  if (!inboxItem) return null;
  const legacy = snapshot.legacy_inbound_webhook_delivery as LegacyInboundDelivery;
  return buildLeadSyncPayloadV1({
    row,
    inboxItem,
    legacyInboundDelivery: legacy,
    idempotency_key: snapshot.idempotency_key,
  });
}

function extractItemSearchIds(parsed: PdEnvelope<unknown> | null, wantType: string): number[] {
  if (!parsed?.data) return [];
  const d = parsed.data as Record<string, unknown> | unknown[];
  const list: unknown[] = Array.isArray(d)
    ? d
    : Array.isArray((d as { items?: unknown }).items)
      ? ((d as { items: unknown[] }).items ?? [])
      : [];
  const ids: number[] = [];
  for (const row of list) {
    if (!row || typeof row !== "object") continue;
    const o = row as Record<string, unknown>;
    const item = (o.item ?? o) as Record<string, unknown> | undefined;
    const id = typeof item?.id === "number" ? item.id : typeof o.id === "number" ? o.id : null;
    const type = String(item?.type ?? o.type ?? "").toLowerCase();
    if (id != null && type === wantType) ids.push(id);
  }
  return ids;
}

async function findPersonIdByEmail(token: string, email: string): Promise<number | null> {
  const r = await pdFetch(token, "GET", "/itemSearch", {
    query: { term: email, item_types: "person", limit: "25" },
  });
  requirePdSuccess(r, "itemSearch_person");
  const ids = extractItemSearchIds(r.parsed, "person");
  const lower = email.toLowerCase();
  for (const id of ids.slice(0, 12)) {
    const pr = await pdFetch(token, "GET", `/persons/${id}`);
    if (pr.parsed?.success !== true) continue;
    const data = pr.parsed?.data as { email?: { value?: string }[] } | undefined;
    const emails = (data?.email ?? []).map((e) => String(e.value ?? "").toLowerCase());
    if (emails.includes(lower)) return id;
  }
  return null;
}

async function getPerson(token: string, id: number): Promise<{ name: string } | null> {
  const r = await pdFetch(token, "GET", `/persons/${id}`);
  if (r.parsed?.success !== true) return null;
  const data = r.parsed?.data as { name?: string } | undefined;
  return { name: String(data?.name ?? "") };
}

async function createPerson(
  token: string,
  input: { name: string; email: string; org_id?: number; owner_id?: number },
): Promise<number> {
  const body: Record<string, unknown> = {
    name: input.name.slice(0, 200),
    email: [{ value: input.email, primary: true, label: "work" }],
  };
  if (input.org_id != null) body.org_id = input.org_id;
  if (input.owner_id != null) body.owner_id = input.owner_id;
  const r = await pdFetch(token, "POST", "/persons", { body });
  requirePdSuccess(r, "person_create");
  const data = r.parsed?.data as { id?: number } | undefined;
  if (typeof data?.id !== "number") {
    throw { status: r.status, parsed: r.parsed, raw: r.raw, op: "person_create_no_id" };
  }
  return data.id;
}

/** Nur leeren Namen füllen — keine Organisation/Owner überschreiben (konservativ). */
async function updatePersonConservative(token: string, id: number, input: { name: string }): Promise<void> {
  const cur = await getPerson(token, id);
  const body: Record<string, unknown> = {};
  if (cur && !cur.name.trim() && input.name.trim()) body.name = input.name.slice(0, 200);
  if (Object.keys(body).length === 0) return;
  const r = await pdFetch(token, "PUT", `/persons/${id}`, { body });
  requirePdSuccess(r, "person_update");
}

async function findOrgIdByExactName(token: string, name: string): Promise<{ id: number | null; ambiguous: boolean }> {
  const r = await pdFetch(token, "GET", "/itemSearch", {
    query: { term: name.trim(), item_types: "organization", limit: "25" },
  });
  requirePdSuccess(r, "itemSearch_org");
  const ids = extractItemSearchIds(r.parsed, "organization");
  const matches: number[] = [];
  const target = name.trim().toLowerCase();
  for (const id of ids.slice(0, 15)) {
    const or = await pdFetch(token, "GET", `/organizations/${id}`);
    if (or.parsed?.success !== true) continue;
    const data = or.parsed?.data as { name?: string } | undefined;
    if (String(data?.name ?? "").trim().toLowerCase() === target) matches.push(id);
  }
  if (matches.length === 1) return { id: matches[0]!, ambiguous: false };
  if (matches.length === 0) return { id: null, ambiguous: false };
  return { id: null, ambiguous: true };
}

async function createOrg(token: string, name: string): Promise<number> {
  const r = await pdFetch(token, "POST", "/organizations", {
    body: { name: name.trim().slice(0, 200) },
  });
  requirePdSuccess(r, "org_create");
  const data = r.parsed?.data as { id?: number } | undefined;
  if (typeof data?.id !== "number") {
    throw { status: r.status, parsed: r.parsed, raw: r.raw, op: "org_create_no_id" };
  }
  return data.id;
}

async function listDealsForPerson(token: string, personId: number): Promise<{ id: number; title: string }[]> {
  const r = await pdFetch(token, "GET", "/deals", {
    query: { person_id: String(personId), limit: "100" },
  });
  requirePdSuccess(r, "deals_by_person");
  const data = r.parsed?.data as unknown;
  const list = Array.isArray(data) ? data : [];
  return list
    .map((row) => {
      const o = row as { id?: number; title?: string };
      return { id: Number(o.id), title: String(o.title ?? "") };
    })
    .filter((x) => Number.isFinite(x.id));
}

function dealTitleForLead(payload: LeadSyncPayloadV1): string {
  const label = payload.company.trim() || payload.name.trim() || payload.business_email;
  const core = `${DEAL_TITLE_PREFIX}${payload.lead_id} | ${label} · ${payload.segment}`;
  return core.slice(0, 400);
}

function dealNoteContent(payload: LeadSyncPayloadV1): string {
  const body = [
    `ComplianceHub Pipedrive-Sync (${payload.contact_latest_seen_at})`,
    "",
    `Nachricht (Auszug): ${(payload.message || "").slice(0, 2000)}`,
    "",
    `Quelle: ${payload.source_page} · Segment: ${payload.segment}`,
    `Route: ${payload.route.route_key} / ${payload.route.queue_label} · Owner (Inbox): ${payload.owner || "—"}`,
    `Triage: ${payload.triage_status} · trace_id: ${payload.trace_id} · lead_id: ${payload.lead_id}`,
    `Kontakt-Anfrage #${payload.contact_inquiry_sequence} von ${payload.contact_submission_count} · duplicate_hint: ${payload.duplicate_hint}`,
  ].join("\n");
  return body.slice(0, 8000);
}

async function createDeal(
  token: string,
  input: {
    title: string;
    person_id: number;
    org_id?: number;
    pipeline_id: number;
    stage_id: number;
    user_id?: number;
  },
): Promise<number> {
  const body: Record<string, unknown> = {
    title: input.title,
    person_id: input.person_id,
    pipeline_id: input.pipeline_id,
    stage_id: input.stage_id,
  };
  if (input.org_id != null) body.org_id = input.org_id;
  if (input.user_id != null) body.user_id = input.user_id;
  const r = await pdFetch(token, "POST", "/deals", { body });
  requirePdSuccess(r, "deal_create");
  const data = r.parsed?.data as { id?: number } | undefined;
  if (typeof data?.id !== "number") {
    throw { status: r.status, parsed: r.parsed, raw: r.raw, op: "deal_create_no_id" };
  }
  return data.id;
}

async function updateDeal(
  token: string,
  dealId: number,
  input: {
    title: string;
    org_id?: number;
    user_id?: number;
  },
): Promise<void> {
  const body: Record<string, unknown> = { title: input.title };
  if (input.org_id != null) body.org_id = input.org_id;
  if (input.user_id != null) body.user_id = input.user_id;
  const r = await pdFetch(token, "PUT", `/deals/${dealId}`, { body });
  requirePdSuccess(r, "deal_update");
}

async function addDealNote(
  token: string,
  dealId: number,
  personId: number,
  content: string,
): Promise<void> {
  const r = await pdFetch(token, "POST", "/notes", {
    body: { content, deal_id: dealId, person_id: personId },
  });
  requirePdSuccess(r, "note_create");
}

function toConnectorError(err: unknown): LeadSyncConnectorResult {
  if (err && typeof err === "object" && "status" in err) {
    const e = err as {
      status: number;
      parsed: PdEnvelope<unknown> | null;
      raw: string;
      op?: string;
    };
    const msg = formatPdError(e.status, e.parsed, e.raw);
    return {
      ok: false,
      http_status: e.status,
      error: `${e.op ?? "pipedrive"}: ${msg}`,
      retryable: classifyPipedriveRetryable(e.status, msg),
    };
  }
  const msg = err instanceof Error ? err.message : String(err);
  return { ok: false, error: `pipedrive: ${msg}`, retryable: true };
}

export async function runPipedriveLeadSyncConnector(snapshot: LeadSyncPayloadV1): Promise<LeadSyncConnectorResult> {
  const token = process.env.PIPEDRIVE_API_TOKEN?.trim();
  if (!token) {
    return { ok: false, error: "pipedrive_token_not_configured", retryable: false };
  }

  const pipelineIdRaw = process.env.PIPEDRIVE_DEFAULT_PIPELINE_ID?.trim();
  const stageIdRaw = process.env.PIPEDRIVE_DEFAULT_STAGE_ID?.trim();
  const pipeline_id = pipelineIdRaw ? Number(pipelineIdRaw) : NaN;
  const stage_id = stageIdRaw ? Number(stageIdRaw) : NaN;
  if (!Number.isFinite(pipeline_id) || !Number.isFinite(stage_id)) {
    return {
      ok: false,
      error:
        "pipedrive: PIPEDRIVE_DEFAULT_PIPELINE_ID and PIPEDRIVE_DEFAULT_STAGE_ID must be set to numeric IDs",
      retryable: false,
    };
  }

  const ownerIdRaw = process.env.PIPEDRIVE_DEFAULT_OWNER_ID?.trim();
  const user_id = ownerIdRaw ? Number(ownerIdRaw) : undefined;
  if (ownerIdRaw && !Number.isFinite(user_id)) {
    return { ok: false, error: "pipedrive: PIPEDRIVE_DEFAULT_OWNER_ID invalid", retryable: false };
  }

  let payload: LeadSyncPayloadV1;
  try {
    const fresh = await resolveFreshPayload(snapshot);
    if (!fresh) {
      return { ok: false, error: "pipedrive: lead_not_found", retryable: false };
    }
    payload = fresh;
  } catch (e) {
    return toConnectorError(e);
  }

  if (!isLeadPipedriveDealEligible(payload)) {
    return {
      ok: false,
      error: "pipedrive: not_deal_eligible (triage/segment/owner/company)",
      retryable: false,
    };
  }

  const email = payload.business_email.trim().toLowerCase();
  const synced_at = new Date().toISOString();

  try {
    let personId = await findPersonIdByEmail(token, email);
    let org_association: LeadSyncPipedriveSyncResult["org_association"] = "skipped_weak_name";
    let orgId: number | undefined;

    const companyName = payload.company.trim();
    if (!isWeakOrgName(companyName)) {
      const orgMatch = await findOrgIdByExactName(token, companyName);
      if (orgMatch.ambiguous) {
        org_association = "skipped_ambiguous";
      } else if (orgMatch.id != null) {
        orgId = orgMatch.id;
        org_association = "linked";
      } else if (process.env.PIPEDRIVE_ALLOW_ORG_CREATE === "1") {
        orgId = await createOrg(token, companyName);
        org_association = "linked";
      } else {
        org_association = "skipped_no_match";
      }
    }

    if (personId == null) {
      personId = await createPerson(token, {
        name: payload.name.trim() || email,
        email,
        org_id: orgId,
        owner_id: user_id,
      });
    } else {
      await updatePersonConservative(token, personId, {
        name: payload.name.trim() || email,
      });
    }

    const deals = await listDealsForPerson(token, personId);
    const marker = `${DEAL_TITLE_PREFIX}${payload.lead_id}`;
    const existing = deals.find((d) => d.title.includes(marker) || d.title.startsWith(marker));

    const title = dealTitleForLead(payload);
    let dealId: number;
    let deal_action: LeadSyncPipedriveSyncResult["deal_action"];

    if (existing) {
      dealId = existing.id;
      deal_action = "updated";
      await updateDeal(token, dealId, {
        title,
        org_id: orgId,
        user_id,
      });
    } else {
      deal_action = "created";
      dealId = await createDeal(token, {
        title,
        person_id: personId,
        org_id: orgId,
        pipeline_id,
        stage_id,
        user_id,
      });
    }

    await addDealNote(token, dealId, personId, dealNoteContent(payload));

    const mock_result: LeadSyncPipedriveSyncResult = {
      system: "pipedrive",
      synced_at,
      person_id: String(personId),
      org_id: orgId != null ? String(orgId) : undefined,
      org_association,
      deal_id: String(dealId),
      deal_action,
      pipeline_id,
      stage_id,
    };

    return { ok: true, http_status: 200, mock_result };
  } catch (e) {
    return toConnectorError(e);
  }
}
