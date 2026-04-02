import "server-only";

import { attachContactRollups, mergeLeadsWithOps } from "@/lib/leadInboxMerge";
import { appendLeadOpsActivity, readLeadOpsState } from "@/lib/leadOpsState";
import {
  buildLeadSyncPayloadV1,
  computeLeadSyncIdempotencyKey,
  defaultMaterialRevisionForIngest,
  LEAD_SYNC_PAYLOAD_VERSION,
  type LegacyInboundDelivery,
} from "@/lib/leadSyncPayload";
import { runLeadSyncConnector } from "@/lib/leadSyncConnectors";
import {
  ensureLeadSyncJob,
  getLeadSyncJobById,
  listProcessableLeadSyncJobs,
  updateLeadSyncJob,
} from "@/lib/leadSyncStore";
import type { LeadSyncJob, LeadSyncJobApi, LeadSyncTarget } from "@/lib/leadSyncTypes";
import { getMergedLeadAdminRow, readAllLeadRecordsMerged } from "@/lib/leadPersistence";

export const LEAD_SYNC_MAX_ATTEMPTS = 6;

export function getEnabledLeadSyncTargets(): LeadSyncTarget[] {
  const t: LeadSyncTarget[] = [];
  if (process.env.LEAD_SYNC_N8N_URL?.trim()) t.push("n8n_webhook");
  if (process.env.LEAD_SYNC_HUBSPOT_STUB === "1") t.push("hubspot_stub");
  if (process.env.LEAD_SYNC_PIPEDRIVE_STUB === "1") t.push("pipedrive_stub");
  return t;
}

export async function enqueueLeadSyncAfterIngest(input: {
  lead_id: string;
  legacyInboundDelivery: LegacyInboundDelivery;
}): Promise<string[]> {
  const targets = getEnabledLeadSyncTargets();
  if (targets.length === 0) return [];

  const row = await getMergedLeadAdminRow(input.lead_id);
  if (!row) return [];

  const allRows = await readAllLeadRecordsMerged();
  const ops = await readLeadOpsState();
  const merged = mergeLeadsWithOps([row], ops);
  const items = attachContactRollups(merged, allRows, ops);
  const inboxItem = items[0];
  if (!inboxItem) return [];

  const material = defaultMaterialRevisionForIngest(row.created_at);
  const jobIds: string[] = [];
  const contactKey = row.lead_contact_key ?? inboxItem.lead_contact_key;

  for (const target of targets) {
    const idempotency_key = computeLeadSyncIdempotencyKey(
      target,
      row.lead_id,
      LEAD_SYNC_PAYLOAD_VERSION,
      material,
    );
    const payload = buildLeadSyncPayloadV1({
      row,
      inboxItem,
      legacyInboundDelivery: input.legacyInboundDelivery,
      idempotency_key,
    });
    const { job, created } = await ensureLeadSyncJob({
      lead_id: row.lead_id,
      lead_contact_key: contactKey,
      target,
      payload_version: LEAD_SYNC_PAYLOAD_VERSION,
      idempotency_key,
      payload_snapshot: payload,
    });
    jobIds.push(job.job_id);
    if (created) {
      try {
        await appendLeadOpsActivity(
          input.lead_id,
          "lead_sync_job_created",
          `${target} job=${job.job_id.slice(0, 8)}`,
        );
      } catch {
        /* ignore */
      }
    }
  }
  return jobIds;
}

function backoffMs(attemptNumber: number): number {
  return Math.min(120_000, 2000 * Math.pow(2, Math.max(0, attemptNumber - 1)));
}

export async function processLeadSyncJobById(jobId: string): Promise<LeadSyncJob | null> {
  let job = await getLeadSyncJobById(jobId);
  if (!job?.payload_snapshot) return job;

  if (job.status === "sent" || job.status === "dead_letter") return job;

  const nowMs = Date.now();
  if (job.status === "failed" && job.next_retry_at && new Date(job.next_retry_at).getTime() > nowMs) {
    return job;
  }

  const attempt = job.attempt_count + 1;
  await updateLeadSyncJob(jobId, (j) => ({
    ...j,
    status: "retrying",
    attempt_count: attempt,
    last_attempt_at: new Date().toISOString(),
    next_retry_at: undefined,
  }));

  job = await getLeadSyncJobById(jobId);
  if (!job?.payload_snapshot) return job;

  const result = await runLeadSyncConnector(job.target, job.payload_snapshot);

  if (result.ok) {
    await updateLeadSyncJob(jobId, (j) => ({
      ...j,
      status: "sent",
      last_error: undefined,
      last_http_status: result.http_status,
      mock_result: result.mock_result,
    }));
    try {
      await appendLeadOpsActivity(
        job.lead_id,
        "lead_sync_sent",
        `${job.target} Versuch ${attempt}`,
      );
    } catch {
      /* ignore */
    }
  } else if (attempt >= LEAD_SYNC_MAX_ATTEMPTS) {
    await updateLeadSyncJob(jobId, (j) => ({
      ...j,
      status: "dead_letter",
      last_error: result.error,
      last_http_status: result.http_status,
    }));
    try {
      await appendLeadOpsActivity(
        job.lead_id,
        "lead_sync_dead_letter",
        `${job.target}: ${result.error ?? "?"}`,
      );
    } catch {
      /* ignore */
    }
  } else {
    const next = new Date(nowMs + backoffMs(attempt)).toISOString();
    await updateLeadSyncJob(jobId, (j) => ({
      ...j,
      status: "failed",
      last_error: result.error,
      last_http_status: result.http_status,
      next_retry_at: next,
    }));
    try {
      await appendLeadOpsActivity(
        job.lead_id,
        "lead_sync_failed",
        `${job.target} (${attempt}/${LEAD_SYNC_MAX_ATTEMPTS}): ${result.error ?? "?"}`,
      );
    } catch {
      /* ignore */
    }
    if (attempt > 1) {
      try {
        await appendLeadOpsActivity(job.lead_id, "lead_sync_retried", job.target);
      } catch {
        /* ignore */
      }
    }
  }

  return getLeadSyncJobById(jobId);
}

export async function processPendingLeadSyncJobs(limit: number): Promise<number> {
  const pending = await listProcessableLeadSyncJobs(limit);
  for (const j of pending) {
    await processLeadSyncJobById(j.job_id);
  }
  return pending.length;
}

export async function manualRetryLeadSyncJob(jobId: string): Promise<LeadSyncJob | null> {
  const before = await getLeadSyncJobById(jobId);
  if (!before) return null;

  await updateLeadSyncJob(jobId, (j) => ({
    ...j,
    status: "pending",
    next_retry_at: undefined,
    last_error: undefined,
    attempt_count: 0,
  }));

  try {
    await appendLeadOpsActivity(
      before.lead_id,
      "lead_sync_retried",
      `manual retry ${before.target} job=${jobId.slice(0, 8)}`,
    );
  } catch {
    /* ignore */
  }

  await processLeadSyncJobById(jobId);
  return getLeadSyncJobById(jobId);
}

/** API-Antwort ohne großen Payload-Body. */
export function redactLeadSyncJobForApi(j: LeadSyncJob): LeadSyncJobApi {
  const { payload_snapshot: _snap, ...rest } = j;
  void _snap;
  return rest;
}
