import "server-only";

import { runHubspotLeadSyncConnector } from "@/lib/hubspotLeadSyncConnector";
import {
  approvedOutboundWebhookUrl,
  crmProviderIsForbiddenInProduction,
  isEnterpriseProductionRuntime,
} from "@/lib/outboundEndpointPolicy";
import { runPipedriveLeadSyncConnector } from "@/lib/pipedriveLeadSyncConnector";
import { readServerSecret } from "@/lib/serverSecret";
import type { LeadSyncConnectorResult, LeadSyncPayloadV1, LeadSyncTarget } from "@/lib/leadSyncTypes";

export type ConnectorResult = LeadSyncConnectorResult;

const N8N_TIMEOUT_MS = 25_000;

export async function runLeadSyncConnector(
  target: LeadSyncTarget,
  payload: LeadSyncPayloadV1,
): Promise<ConnectorResult> {
  if (
    (target === "hubspot" || target === "hubspot_stub") &&
    crmProviderIsForbiddenInProduction("hubspot")
  ) {
    return { ok: false, error: "hubspot_forbidden_by_provider_policy", retryable: false };
  }
  if (
    (target === "pipedrive" || target === "pipedrive_stub") &&
    crmProviderIsForbiddenInProduction("pipedrive")
  ) {
    return { ok: false, error: "pipedrive_forbidden_by_provider_policy", retryable: false };
  }
  switch (target) {
    case "n8n_webhook":
      return runN8nWebhookConnector(payload);
    case "hubspot":
      return runHubspotLeadSyncConnector(payload);
    case "hubspot_stub":
      return runHubspotStubConnector(payload);
    case "pipedrive":
      return runPipedriveLeadSyncConnector(payload);
    case "pipedrive_stub":
      return runPipedriveStubConnector(payload);
    default:
      return { ok: false, error: "unknown_target" };
  }
}

async function runN8nWebhookConnector(payload: LeadSyncPayloadV1): Promise<ConnectorResult> {
  const configuredUrl = process.env.LEAD_SYNC_N8N_URL?.trim();
  if (!configuredUrl) {
    return { ok: false, error: "n8n_url_not_configured" };
  }
  const url = approvedOutboundWebhookUrl(configuredUrl, "LEAD_SYNC_N8N_URL");
  const secret = readServerSecret({
    environmentVariable: "LEAD_SYNC_N8N_SECRET",
    fileEnvironmentVariable: "LEAD_SYNC_N8N_SECRET_FILE",
    minimumBytes: 32,
    required: isEnterpriseProductionRuntime(),
  });
  let timer: ReturnType<typeof setTimeout> | null = null;
  try {
    const controller = new AbortController();
    timer = setTimeout(() => controller.abort(), N8N_TIMEOUT_MS);
    const r = await fetch(url, {
      method: "POST",
      redirect: "manual",
      headers: {
        "Content-Type": "application/json",
        ...(secret ? { Authorization: `Bearer ${secret}` } : {}),
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
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
  } finally {
    if (timer) clearTimeout(timer);
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
