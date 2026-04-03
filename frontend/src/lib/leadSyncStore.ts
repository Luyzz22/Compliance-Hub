import { randomUUID } from "crypto";
import { mkdir, readFile, rename, writeFile } from "fs/promises";
import { dirname, join } from "path";

import "server-only";

import type { LeadSyncJob, LeadSyncPayloadV1, LeadSyncTarget } from "@/lib/leadSyncTypes";

const STORE_VERSION = 1;

type JobsStoreFile = {
  version: number;
  jobs: Record<string, LeadSyncJob>;
  /** idempotency_key → job_id */
  idempotency_index: Record<string, string>;
};

function resolveSyncStorePath(): string {
  const fromEnv = process.env.LEAD_SYNC_JOBS_STORE_PATH?.trim();
  if (fromEnv) return fromEnv;
  if (process.env.VERCEL) {
    return join("/tmp", "compliancehub-lead-sync-jobs.json");
  }
  return join(process.cwd(), "data", "lead-inquiries", "sync-jobs.json");
}

function emptyStore(): JobsStoreFile {
  return { version: STORE_VERSION, jobs: {}, idempotency_index: {} };
}

export async function readLeadSyncStore(): Promise<JobsStoreFile> {
  const path = resolveSyncStorePath();
  try {
    const raw = await readFile(path, "utf8");
    const p = JSON.parse(raw) as JobsStoreFile;
    if (p?.version !== STORE_VERSION || typeof p.jobs !== "object" || !p.jobs) {
      return emptyStore();
    }
    if (typeof p.idempotency_index !== "object" || !p.idempotency_index) {
      p.idempotency_index = {};
    }
    return p;
  } catch {
    return emptyStore();
  }
}

export async function writeLeadSyncStore(store: JobsStoreFile): Promise<void> {
  const path = resolveSyncStorePath();
  await mkdir(dirname(path), { recursive: true });
  const tmp = `${path}.tmp`;
  await writeFile(tmp, `${JSON.stringify(store)}\n`, "utf8");
  await rename(tmp, path);
}

export async function getLeadSyncJobById(jobId: string): Promise<LeadSyncJob | null> {
  const s = await readLeadSyncStore();
  return s.jobs[jobId] ?? null;
}

export async function listLeadSyncJobsForLead(leadId: string): Promise<LeadSyncJob[]> {
  const s = await readLeadSyncStore();
  return Object.values(s.jobs)
    .filter((j) => j.lead_id === leadId)
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
}

/** Alle Sync-Jobs (für interne Aggregationen, z. B. GTM-Dashboard). */
export async function listAllLeadSyncJobs(): Promise<LeadSyncJob[]> {
  const s = await readLeadSyncStore();
  return Object.values(s.jobs);
}

/**
 * Legt einen Job an, wenn für dieselbe idempotency_key noch keiner existiert.
 */
export async function ensureLeadSyncJob(input: {
  lead_id: string;
  lead_contact_key: string;
  target: LeadSyncTarget;
  payload_version: string;
  idempotency_key: string;
  payload_snapshot: LeadSyncPayloadV1;
}): Promise<{ job: LeadSyncJob; created: boolean }> {
  const store = await readLeadSyncStore();
  const existingId = store.idempotency_index[input.idempotency_key];
  if (existingId && store.jobs[existingId]) {
    return { job: store.jobs[existingId]!, created: false };
  }

  const now = new Date().toISOString();
  const job: LeadSyncJob = {
    job_id: randomUUID(),
    lead_id: input.lead_id,
    lead_contact_key: input.lead_contact_key,
    target: input.target,
    payload_version: input.payload_version,
    status: "pending",
    attempt_count: 0,
    idempotency_key: input.idempotency_key,
    created_at: now,
    updated_at: now,
    payload_snapshot: input.payload_snapshot,
  };
  store.jobs[job.job_id] = job;
  store.idempotency_index[input.idempotency_key] = job.job_id;
  await writeLeadSyncStore(store);
  return { job, created: true };
}

export async function updateLeadSyncJob(
  jobId: string,
  mutator: (job: LeadSyncJob) => LeadSyncJob,
): Promise<LeadSyncJob | null> {
  const store = await readLeadSyncStore();
  const prev = store.jobs[jobId];
  if (!prev) return null;
  const next = mutator({ ...prev });
  next.updated_at = new Date().toISOString();
  store.jobs[jobId] = next;
  await writeLeadSyncStore(store);
  return next;
}

export async function listProcessableLeadSyncJobs(limit: number): Promise<LeadSyncJob[]> {
  const s = await readLeadSyncStore();
  const now = Date.now();
  const list = Object.values(s.jobs).filter((j) => {
    if (j.status === "sent") return false;
    if (j.status === "dead_letter") return false;
    if (j.status === "pending") return true;
    if (j.status === "retrying") return true;
    if (j.status === "failed") {
      if (!j.next_retry_at) return true;
      return new Date(j.next_retry_at).getTime() <= now;
    }
    return false;
  });
  list.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
  return list.slice(0, limit);
}
