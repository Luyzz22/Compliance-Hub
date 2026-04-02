import "server-only";

import type { LeadSyncConnectorResult, LeadSyncPayloadV1 } from "@/lib/leadSyncTypes";

const HUBSPOT_API = "https://api.hubapi.com";
const REQUEST_TIMEOUT_MS = 28_000;
/** HubSpot-defined: note → contact (see CRM Notes API). */
const NOTE_TO_CONTACT_TYPE_ID = 202;

/** Ergebnis in `mock_result` für Admin-UI / Debugging (keine Secrets). */
export type LeadSyncHubSpotSyncResult = {
  system: "hubspot";
  synced_at: string;
  contact_id: string;
  company_id?: string;
  company_association: "linked" | "skipped_no_match" | "skipped_ambiguous" | "skipped_weak_name" | "skipped_create_disabled";
  note_id?: string;
  note_action: "created" | "skipped_existing";
  pipeline_hint?: string;
};

type HubSpotErrorBody = {
  status?: string;
  message?: string;
  category?: string;
  errors?: { message?: string }[];
};

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function splitName(full: string): { firstname: string; lastname: string } {
  const t = full.trim();
  if (!t) return { firstname: "Website Lead", lastname: "" };
  const i = t.indexOf(" ");
  if (i <= 0) return { firstname: t.slice(0, 120), lastname: "" };
  return {
    firstname: t.slice(0, i).slice(0, 120),
    lastname: t.slice(i + 1).trim().slice(0, 120),
  };
}

function isWeakCompanyName(name: string): boolean {
  const t = name.trim();
  if (t.length < 2) return true;
  return /^(n\/a|na|none|unknown|unbekannt|test|xxx|-+)$/i.test(t);
}

function classifyHubSpotRetryable(status: number, body: HubSpotErrorBody | null): boolean {
  if (status === 429) return true;
  if (status >= 500) return true;
  if (status === 408) return true;
  if (status === 401 || status === 403) return false;
  if (status === 404) return false;
  if (status === 400) {
    const msg = (body?.message ?? "").toLowerCase();
    if (msg.includes("invalid") && msg.includes("token")) return false;
    if (body?.category === "VALIDATION_ERROR") return false;
    if (msg.includes("property") && msg.includes("does not exist")) return false;
    return false;
  }
  if (status >= 400) return false;
  return true;
}

function formatHubSpotError(status: number, rawText: string, parsed: HubSpotErrorBody | null): string {
  const parts = [`http_${status}`];
  if (parsed?.message) parts.push(parsed.message);
  else if (parsed?.errors?.[0]?.message) parts.push(parsed.errors[0].message!);
  else if (rawText) parts.push(rawText.slice(0, 280));
  return parts.join(": ");
}

async function hubspotFetch(
  token: string,
  path: string,
  init: RequestInit,
): Promise<{ status: number; text: string; json: HubSpotErrorBody | null }> {
  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const r = await fetch(`${HUBSPOT_API}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
        ...((init.headers as Record<string, string>) ?? {}),
      },
    });
    const text = await r.text();
    let json: HubSpotErrorBody | null = null;
    try {
      json = JSON.parse(text) as HubSpotErrorBody;
    } catch {
      /* ignore */
    }
    return { status: r.status, text, json };
  } finally {
    clearTimeout(t);
  }
}

function strVal(v: string | null | undefined): string {
  return typeof v === "string" ? v.trim() : "";
}

function buildOptionalCustomProps(payload: LeadSyncPayloadV1): Record<string, string> {
  const out: Record<string, string> = {};
  const ck = process.env.HUBSPOT_PROPERTY_CONTACT_KEY?.trim();
  const ak = process.env.HUBSPOT_PROPERTY_ACCOUNT_KEY?.trim();
  const seg = process.env.HUBSPOT_PROPERTY_SEGMENT?.trim();
  const src = process.env.HUBSPOT_PROPERTY_SOURCE_PAGE?.trim();
  const seen = process.env.HUBSPOT_PROPERTY_LATEST_INQUIRY_AT?.trim();
  if (ck) out[ck] = payload.lead_contact_key;
  if (ak && payload.lead_account_key) out[ak] = payload.lead_account_key;
  if (seg) out[seg] = payload.segment;
  if (src) out[src] = payload.source_page;
  if (seen) out[seen] = payload.contact_latest_seen_at;
  return out;
}

async function searchContactByEmail(
  token: string,
  email: string,
): Promise<{ id: string; properties: Record<string, string | null> } | null> {
  const r = await hubspotFetch(token, "/crm/v3/objects/contacts/search", {
    method: "POST",
    body: JSON.stringify({
      filterGroups: [
        { filters: [{ propertyName: "email", operator: "EQ", value: email.toLowerCase() }] },
      ],
      properties: ["email", "firstname", "lastname", "company", "hubspot_owner_id"],
      limit: 1,
    }),
  });
  if (r.status !== 200) {
    throw { status: r.status, text: r.text, json: r.json, op: "contact_search" };
  }
  const data = JSON.parse(r.text) as { results?: { id: string; properties?: Record<string, string | null> }[] };
  const row = data.results?.[0];
  if (!row) return null;
  return { id: row.id, properties: row.properties ?? {} };
}

async function createContact(
  token: string,
  props: Record<string, string>,
): Promise<{ id: string }> {
  const r = await hubspotFetch(token, "/crm/v3/objects/contacts", {
    method: "POST",
    body: JSON.stringify({ properties: props }),
  });
  if (r.status !== 201 && r.status !== 200) {
    throw { status: r.status, text: r.text, json: r.json, op: "contact_create" };
  }
  const data = JSON.parse(r.text) as { id: string };
  return { id: data.id };
}

async function patchContact(token: string, id: string, props: Record<string, string>): Promise<void> {
  if (Object.keys(props).length === 0) return;
  const r = await hubspotFetch(token, `/crm/v3/objects/contacts/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ properties: props }),
  });
  if (r.status !== 200) {
    throw { status: r.status, text: r.text, json: r.json, op: "contact_patch" };
  }
}

function conservativeContactProps(
  existing: Record<string, string | null>,
  incoming: {
    firstname: string;
    lastname: string;
    company: string;
    ownerId?: string;
    custom: Record<string, string>;
  },
): Record<string, string> {
  const patch: Record<string, string> = {};
  if (!strVal(existing.firstname) && incoming.firstname) patch.firstname = incoming.firstname;
  if (!strVal(existing.lastname) && incoming.lastname) patch.lastname = incoming.lastname;
  if (!strVal(existing.company) && incoming.company) patch.company = incoming.company;
  if (!strVal(existing.hubspot_owner_id) && incoming.ownerId) {
    patch.hubspot_owner_id = incoming.ownerId;
  }
  for (const [k, v] of Object.entries(incoming.custom)) {
    if (!v) continue;
    const cur = existing[k];
    if (!strVal(cur)) patch[k] = v;
  }
  return patch;
}

async function searchCompanyByExactName(token: string, name: string): Promise<{ count: number; id?: string }> {
  const r = await hubspotFetch(token, "/crm/v3/objects/companies/search", {
    method: "POST",
    body: JSON.stringify({
      filterGroups: [{ filters: [{ propertyName: "name", operator: "EQ", value: name }] }],
      properties: ["name"],
      limit: 5,
    }),
  });
  if (r.status !== 200) {
    throw { status: r.status, text: r.text, json: r.json, op: "company_search" };
  }
  const data = JSON.parse(r.text) as { total?: number; results?: { id: string }[] };
  const total =
    typeof data.total === "number" ? data.total : (data.results?.length ?? 0);
  if (total === 1 && data.results?.[0]) return { count: 1, id: data.results[0].id };
  if (total === 0) return { count: 0 };
  return { count: total };
}

async function createCompany(token: string, name: string): Promise<{ id: string }> {
  const r = await hubspotFetch(token, "/crm/v3/objects/companies", {
    method: "POST",
    body: JSON.stringify({ properties: { name } }),
  });
  if (r.status !== 201 && r.status !== 200) {
    throw { status: r.status, text: r.text, json: r.json, op: "company_create" };
  }
  const data = JSON.parse(r.text) as { id: string };
  return { id: data.id };
}

async function associateContactToCompany(token: string, contactId: string, companyId: string): Promise<void> {
  const r = await hubspotFetch(token, "/crm/v3/associations/contacts/companies/batch/create", {
    method: "POST",
    body: JSON.stringify({
      inputs: [{ from: { id: contactId }, to: { id: companyId }, type: "contact_to_company" }],
    }),
  });
  if (r.status === 200 || r.status === 201) return;
  const msg = (r.json?.message ?? r.text).toLowerCase();
  if (r.status === 400 && (msg.includes("already") || msg.includes("existing"))) return;
  throw { status: r.status, text: r.text, json: r.json, op: "association_contact_company" };
}

async function listNoteIdsForContact(token: string, contactId: string, limit: number): Promise<string[]> {
  const r = await hubspotFetch(
    token,
    `/crm/v3/objects/contacts/${contactId}/associations/notes?limit=${limit}`,
    { method: "GET" },
  );
  if (r.status !== 200) {
    throw { status: r.status, text: r.text, json: r.json, op: "list_note_associations" };
  }
  const data = JSON.parse(r.text) as { results?: { id?: string; toObjectId?: string }[] };
  return (data.results ?? [])
    .map((x) => String(x.id ?? x.toObjectId ?? ""))
    .filter(Boolean);
}

async function batchReadNoteBodies(
  token: string,
  ids: string[],
): Promise<{ id: string; body: string }[]> {
  if (ids.length === 0) return [];
  const r = await hubspotFetch(token, "/crm/v3/objects/notes/batch/read", {
    method: "POST",
    body: JSON.stringify({
      inputs: ids.map((id) => ({ id })),
      properties: ["hs_note_body"],
    }),
  });
  if (r.status !== 200) {
    throw { status: r.status, text: r.text, json: r.json, op: "notes_batch_read" };
  }
  const data = JSON.parse(r.text) as {
    results?: { id: string; properties?: { hs_note_body?: string } }[];
  };
  return (data.results ?? []).map((row) => ({
    id: row.id,
    body: row.properties?.hs_note_body ?? "",
  }));
}

function inquiryMarker(leadId: string): string {
  return `COMPLIANCEHUB_LEAD_INQUIRY_ID:${leadId}`;
}

async function findExistingInquiryNote(
  token: string,
  contactId: string,
  leadId: string,
): Promise<string | null> {
  const marker = inquiryMarker(leadId);
  const noteIds = await listNoteIdsForContact(token, contactId, 40);
  if (noteIds.length === 0) return null;
  const bodies = await batchReadNoteBodies(token, noteIds);
  for (const row of bodies) {
    if (row.body.includes(marker)) return row.id;
  }
  return null;
}

async function createNoteForContact(
  token: string,
  contactId: string,
  payload: LeadSyncPayloadV1,
  ownerId?: string,
): Promise<{ id: string }> {
  const hint = process.env.HUBSPOT_PIPELINE_HINT?.trim();
  const lines = [
    `<p><strong>${inquiryMarker(payload.lead_id)}</strong></p>`,
    `<p>${escapeHtml(payload.message || "(keine Nachricht)")}</p>`,
    "<hr/>",
    `<p>Quelle: ${escapeHtml(payload.source_page)} · Segment: ${escapeHtml(payload.segment)}</p>`,
    `<p>Route: ${escapeHtml(payload.route.route_key)} / ${escapeHtml(payload.route.queue_label)} · Priorität: ${escapeHtml(payload.route.priority)} · SLA: ${escapeHtml(payload.route.sla_bucket)}</p>`,
    `<p>Triage: ${escapeHtml(payload.triage_status)} · Anfrage #${payload.contact_inquiry_sequence} von ${payload.contact_submission_count} (Kontakt)</p>`,
    `<p>trace_id: ${escapeHtml(payload.trace_id)} · lead_id: ${escapeHtml(payload.lead_id)}</p>`,
    `<p>lead_contact_key: ${escapeHtml(payload.lead_contact_key)}${payload.lead_account_key ? ` · lead_account_key: ${escapeHtml(payload.lead_account_key)}` : ""}</p>`,
    `<p>duplicate_hint: ${escapeHtml(payload.duplicate_hint)}</p>`,
  ];
  if (hint) {
    lines.splice(2, 0, `<p>Pipeline-Hinweis (intern): ${escapeHtml(hint)}</p>`);
  }
  const hs_note_body = lines.join("\n");
  const props: Record<string, string | number> = {
    hs_timestamp: Date.now(),
    hs_note_body,
  };
  if (ownerId) props.hubspot_owner_id = ownerId;

  const r = await hubspotFetch(token, "/crm/v3/objects/notes", {
    method: "POST",
    body: JSON.stringify({
      properties: props,
      associations: [
        {
          to: { id: contactId },
          types: [{ associationCategory: "HUBSPOT_DEFINED", associationTypeId: NOTE_TO_CONTACT_TYPE_ID }],
        },
      ],
    }),
  });
  if (r.status !== 201 && r.status !== 200) {
    throw { status: r.status, text: r.text, json: r.json, op: "note_create" };
  }
  const data = JSON.parse(r.text) as { id: string };
  return { id: data.id };
}

function toConnectorError(err: unknown): LeadSyncConnectorResult {
  if (err && typeof err === "object" && "status" in err) {
    const e = err as { status: number; text: string; json: HubSpotErrorBody | null; op?: string };
    const retryable = classifyHubSpotRetryable(e.status, e.json);
    return {
      ok: false,
      http_status: e.status,
      error: `${e.op ?? "hubspot"}: ${formatHubSpotError(e.status, e.text, e.json)}`,
      retryable,
    };
  }
  const msg = err instanceof Error ? err.message : String(err);
  return { ok: false, error: `hubspot: ${msg}`, retryable: true };
}

/** Echter HubSpot-Sync: Kontakt upsert, konservative Firma, idempotente Notiz pro Inquiry. */
export async function runHubspotLeadSyncConnector(payload: LeadSyncPayloadV1): Promise<LeadSyncConnectorResult> {
  const token = process.env.HUBSPOT_ACCESS_TOKEN?.trim();
  if (!token) {
    return { ok: false, error: "hubspot_token_not_configured", retryable: false };
  }

  const email = payload.business_email?.trim().toLowerCase();
  if (!email || !email.includes("@")) {
    return { ok: false, error: "hubspot: invalid business_email", retryable: false };
  }

  const ownerId = process.env.HUBSPOT_DEFAULT_OWNER_ID?.trim();
  const { firstname, lastname } = splitName(payload.name);
  const companyName = payload.company?.trim() ?? "";
  const customProps = buildOptionalCustomProps(payload);
  const synced_at = new Date().toISOString();
  const pipeline_hint = process.env.HUBSPOT_PIPELINE_HINT?.trim();

  let contactId: string;

  try {
    const existing = await searchContactByEmail(token, email);
    if (existing) {
      contactId = existing.id;
      const patch = conservativeContactProps(existing.properties, {
        firstname,
        lastname,
        company: companyName,
        ownerId,
        custom: customProps,
      });
      await patchContact(token, contactId, patch);
    } else {
      const createProps: Record<string, string> = {
        email,
        firstname,
        ...(lastname ? { lastname } : {}),
        ...(companyName ? { company: companyName } : {}),
        ...(ownerId ? { hubspot_owner_id: ownerId } : {}),
        ...customProps,
      };
      const created = await createContact(token, createProps);
      contactId = created.id;
    }

    let company_association: LeadSyncHubSpotSyncResult["company_association"] = "skipped_weak_name";
    let company_id: string | undefined;

    if (!isWeakCompanyName(companyName)) {
      const match = await searchCompanyByExactName(token, companyName);
      if (match.count === 1 && match.id) {
        company_id = match.id;
        try {
          await associateContactToCompany(token, contactId, match.id);
          company_association = "linked";
        } catch (e) {
          return toConnectorError(e);
        }
      } else if (match.count === 0) {
        if (process.env.HUBSPOT_ALLOW_COMPANY_CREATE === "1") {
          try {
            const co = await createCompany(token, companyName);
            company_id = co.id;
            await associateContactToCompany(token, contactId, co.id);
            company_association = "linked";
          } catch (e) {
            return toConnectorError(e);
          }
        } else {
          company_association = "skipped_no_match";
        }
      } else {
        company_association = "skipped_ambiguous";
      }
    }

    const existingNote = await findExistingInquiryNote(token, contactId, payload.lead_id);
    let note_id: string | undefined;
    let note_action: LeadSyncHubSpotSyncResult["note_action"] = "skipped_existing";

    if (existingNote) {
      note_id = existingNote;
    } else {
      const note = await createNoteForContact(token, contactId, payload, ownerId);
      note_id = note.id;
      note_action = "created";
    }

    const mock_result: LeadSyncHubSpotSyncResult = {
      system: "hubspot",
      synced_at,
      pipeline_hint,
      contact_id: contactId,
      company_id,
      company_association,
      note_id,
      note_action,
    };

    return { ok: true, http_status: 200, mock_result };
  } catch (err) {
    return toConnectorError(err);
  }
}
