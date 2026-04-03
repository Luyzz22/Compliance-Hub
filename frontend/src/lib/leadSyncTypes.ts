/**
 * Wave 28 – Lead-Sync-Jobs (getrennt von Roh-Anfrage / JSONL lead_inquiry).
 */

export type LeadSyncTarget =
  | "n8n_webhook"
  | "hubspot"
  | "hubspot_stub"
  | "pipedrive"
  | "pipedrive_stub";

export type LeadSyncJobStatus =
  | "pending"
  | "retrying"
  | "sent"
  | "failed"
  | "dead_letter";

/** Stabiler Vertrag für Downstream (n8n / CRM), snake_case. */
export type LeadSyncPayloadV1 = {
  schema_version: "1.0";
  idempotency_key: string;
  lead_id: string;
  trace_id: string;
  created_at: string;
  /** Inquiry */
  source_page: string;
  segment: string;
  name: string;
  business_email: string;
  company: string;
  message: string;
  route: {
    route_key: string;
    queue_label: string;
    priority: string;
    sla_bucket: string;
  };
  /** Kontakt-Rollup (Wave 27) */
  lead_contact_key: string;
  lead_account_key: string | null;
  contact_inquiry_sequence: number;
  contact_first_seen_at: string;
  contact_latest_seen_at: string;
  contact_submission_count: number;
  duplicate_hint: string;
  /** Interne Triage zum Sync-Zeitpunkt */
  triage_status: string;
  owner: string;
  /** Pipeline / Weiterleitung */
  pipeline_status: string;
  forwarding_status: string;
  /** Hinweis: separates Legacy-Webhook (Wave 25) vs. Sync-Framework */
  legacy_inbound_webhook_delivery: "forwarded" | "stored" | "stored_forward_failed" | "not_configured";
};

export type LeadSyncJob = {
  job_id: string;
  lead_id: string;
  lead_contact_key: string;
  target: LeadSyncTarget;
  /** Sync-Payload-Schema, z. B. 1.0 */
  payload_version: string;
  status: LeadSyncJobStatus;
  attempt_count: number;
  idempotency_key: string;
  created_at: string;
  updated_at: string;
  last_attempt_at?: string;
  last_error?: string;
  last_http_status?: number;
  next_retry_at?: string;
  /** Downstream-Ergebnis (Stub, n8n-Meta, HubSpot-IDs usw.; keine Secrets). */
  mock_result?: unknown;
  /** Fixierter Payload pro Job (Retries senden dasselbe Snapshot). */
  payload_snapshot?: LeadSyncPayloadV1;
};

/** API-/UI-Ansicht ohne großen Payload-Snapshot. */
export type LeadSyncJobApi = Omit<LeadSyncJob, "payload_snapshot">;

/** Rückgabe eines Downstream-Connectors (inkl. Retry-Hinweis für den Dispatcher). */
export type LeadSyncConnectorResult = {
  ok: boolean;
  http_status?: number;
  error?: string;
  mock_result?: unknown;
  /** `false` = sofort Dead Letter (z. B. Auth/Validation). */
  retryable?: boolean;
};
