import "server-only";

import { runHubspotLeadSyncConnector } from "@/lib/hubspotLeadSyncConnector";
import type { LeadSyncConnectorResult, LeadSyncPayloadV1, LeadSyncTarget } from "@/lib/leadSyncTypes";

export type ConnectorResult = LeadSyncConnectorResult;

const N8N_TIMEOUT_MS = 25_000;

export async function runLeadSyncConnector(
  target: LeadSyncTarget,
  payload: LeadSyncPayloadV1,
): Promise<ConnectorResult> {
  switch (target) {
    case "n8n_webhook":
      return runN8nWebhookConnector(payload);
    case "hubspot":
      return runHubspotLeadSyncConnector(payload);
    case "hubspot_stub":
      return runHubspotStubConnector(payload);
    case "pipedrive_stub":
      return runPipedriveStubConnector(payload);
    default:
      return { ok: false, error: "unknown_target" };
  }
}

async function runN8nWebhookConnector(payload: LeadSyncPayloadV1): Promise<ConnectorResult> {
  const url = process.env.LEAD_SYNC_N8N_URL?.trim();
  if (!url) {
    return { ok: false, error: "n8n_url_not_configured" };
  }
  try {
    const controller = new AbortController();
    const t = setTimeout(() => controller.abort(), N8N_TIMEOUT_MS);
    const secret = process.env.LEAD_SYNC_N8N_SECRET?.trim();
    const r = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(secret ? { Authorization: `Bearer ${secret}` } : {}),
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    clearTimeout(t);
    if (r.ok) {
      return { ok: true, http_status: r.status, mock_result: { target: "n8n_webhook", status: r.status } };
    }
    const errText = await r.text().catch(() => "");
    return {
      ok: false,
      http_status: r.status,
      error: `http_${r.status}${errText ? ` ${errText.slice(0, 200)}` : ""}`,
    };
  } catch (e) {
    return {
      ok: false,
      error: e instanceof Error ? e.message : String(e),
    };
  }
}

/**
 * Konzept: Upsert Kontakt per E-Mail / contact_key, Notiz pro Inquiry anhängen.
 */
function runHubspotStubConnector(payload: LeadSyncPayloadV1): ConnectorResult {
  const conceptual = {
    system: "hubspot_stub",
    upsert_contact: {
      match_by: "email_and_external_id",
      email: payload.business_email,
      external_contact_key: payload.lead_contact_key,
      properties: {
        company: payload.company,
        last_seen: payload.contact_latest_seen_at,
        inquiry_count: payload.contact_submission_count,
      },
    },
    append_timeline: {
      type: "note",
      body_preview: payload.message.slice(0, 500),
      lead_id: payload.lead_id,
      trace_id: payload.trace_id,
    },
    idempotency_key: payload.idempotency_key,
  };
  return {
    ok: true,
    http_status: 200,
    mock_result: conceptual,
  };
}

/**
 * Konzept: Person + Deal-Notiz / Aktivität.
 */
function runPipedriveStubConnector(payload: LeadSyncPayloadV1): ConnectorResult {
  const conceptual = {
    system: "pipedrive_stub",
    upsert_person: {
      email: payload.business_email,
      name: payload.name,
      org_name: payload.company,
      custom_field_contact_key: payload.lead_contact_key,
    },
    add_activity: {
      type: "note",
      subject: `Lead inquiry ${payload.lead_id.slice(0, 8)}`,
      lead_id: payload.lead_id,
      sequence: payload.contact_inquiry_sequence,
    },
    idempotency_key: payload.idempotency_key,
  };
  return {
    ok: true,
    http_status: 200,
    mock_result: conceptual,
  };
}
