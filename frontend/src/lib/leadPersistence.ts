import { appendFile, mkdir, readFile } from "fs/promises";
import { dirname, join } from "path";

import {
  deriveLeadAccountKeyFromStoredRecord,
  deriveLeadContactKeyFromStoredRecord,
} from "@/lib/leadIdentity";
import type { LeadDuplicateHint } from "@/lib/leadIdentity";
import type { LeadOutboundPayloadV1 } from "@/lib/leadOutbound";

export type LeadStoreStatus = "received" | "forwarded" | "failed" | "reviewed";

export type LeadStoreRecord = {
  _kind: "lead_inquiry";
  lead_id: string;
  trace_id: string;
  status: LeadStoreStatus;
  created_at: string;
  forwarded_at?: string;
  webhook_error?: string;
  outbound: LeadOutboundPayloadV1;
  /** Wave 27 – gespiegelt für schnelle JSONL-Scans (auch in outbound 1.1). */
  lead_contact_key?: string;
  lead_account_key?: string | null;
  contact_inquiry_sequence?: number;
  contact_first_seen_at?: string;
  contact_latest_seen_at?: string;
  duplicate_hint?: LeadDuplicateHint;
};

export type LeadWebhookResultLine = {
  _kind: "webhook_result";
  lead_id: string;
  trace_id: string;
  ok: boolean;
  at: string;
  error?: string;
};

function resolveStorePath(): string {
  const fromEnv = process.env.LEAD_INQUIRY_STORE_PATH?.trim();
  if (fromEnv) return fromEnv;
  if (process.env.VERCEL) {
    return join("/tmp", "compliancehub-lead-inquiries.jsonl");
  }
  return join(process.cwd(), "data", "lead-inquiries", "store.jsonl");
}

export async function persistLeadReceived(record: LeadStoreRecord): Promise<{ path: string }> {
  const path = resolveStorePath();
  await mkdir(dirname(path), { recursive: true });
  await appendFile(path, `${JSON.stringify(record)}\n`, "utf8");
  return { path };
}

export async function appendLeadWebhookResult(line: LeadWebhookResultLine): Promise<void> {
  const path = resolveStorePath();
  await appendFile(path, `${JSON.stringify(line)}\n`, "utf8");
}

export type LeadAdminRow = LeadStoreRecord & {
  webhook_ok?: boolean;
  webhook_at?: string;
  webhook_error?: string;
};

async function mergeAllLeadAdminRowsFromPath(path: string): Promise<LeadAdminRow[]> {
  try {
    const raw = await readFile(path, "utf8");
    const lines = raw.trim().split("\n").filter(Boolean);
    const byId = new Map<string, LeadAdminRow>();
    for (const line of lines) {
      let row: unknown;
      try {
        row = JSON.parse(line);
      } catch {
        continue;
      }
      const o = row as { _kind?: string; lead_id?: string };
      if (o._kind === "lead_inquiry" && o.lead_id) {
        byId.set(o.lead_id, { ...(row as LeadStoreRecord) });
      }
      if (o._kind === "webhook_result" && o.lead_id) {
        const base = byId.get(o.lead_id);
        const wr = row as LeadWebhookResultLine;
        if (base) {
          base.webhook_ok = wr.ok;
          base.webhook_at = wr.at;
          base.webhook_error = wr.error;
          base.status = wr.ok ? "forwarded" : "failed";
          base.forwarded_at = wr.ok ? wr.at : base.forwarded_at;
        }
      }
    }
    return Array.from(byId.values()).sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    );
  } catch {
    return [];
  }
}

/** Alle Anfragen (für Kontakt-Rollups / Historie). */
export async function readAllLeadRecordsMerged(): Promise<LeadAdminRow[]> {
  return mergeAllLeadAdminRowsFromPath(resolveStorePath());
}

export function computeContactKeyStatsFromRows(
  all: LeadAdminRow[],
  contactKey: string,
): { prior_count: number; first_seen_at: string | null; prior_lead_ids: string[] } {
  const matching = all
    .filter((r) => deriveLeadContactKeyFromStoredRecord(r) === contactKey)
    .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
  return {
    prior_count: matching.length,
    first_seen_at: matching[0]?.created_at ?? null,
    prior_lead_ids: matching.map((m) => m.lead_id),
  };
}

/** Andere Kontakt-Keys unter derselben Account-Gruppe (Firma/Domain) – nur Hinweis, kein Merge. */
export function countOtherContactKeysOnAccount(
  all: LeadAdminRow[],
  accountKey: string | null,
  excludeContactKey: string,
): number {
  if (!accountKey) return 0;
  const set = new Set<string>();
  for (const r of all) {
    if (deriveLeadAccountKeyFromStoredRecord(r) !== accountKey) continue;
    set.add(deriveLeadContactKeyFromStoredRecord(r));
  }
  set.delete(excludeContactKey);
  return set.size;
}

/** Liest die gesamte JSONL und liefert die erste passende `lead_inquiry`-Zeile (Outbound inkl.). */
export async function findLeadInquiryRecord(leadId: string): Promise<LeadStoreRecord | null> {
  const path = resolveStorePath();
  try {
    const raw = await readFile(path, "utf8");
    const lines = raw.trim().split("\n").filter(Boolean);
    let found: LeadStoreRecord | null = null;
    for (const line of lines) {
      try {
        const row = JSON.parse(line) as { _kind?: string; lead_id?: string };
        if (row._kind === "lead_inquiry" && row.lead_id === leadId) {
          found = row as LeadStoreRecord;
        }
      } catch {
        /* skip */
      }
    }
    return found;
  } catch {
    return null;
  }
}

/** Einzelnen Lead inkl. Webhook-Zeilen zusammenführen (unabhängig vom List-Limit). */
export async function getMergedLeadAdminRow(leadId: string): Promise<LeadAdminRow | null> {
  const base = await findLeadInquiryRecord(leadId);
  if (!base) return null;
  const row: LeadAdminRow = { ...base };
  const path = resolveStorePath();
  try {
    const raw = await readFile(path, "utf8");
    const lines = raw.trim().split("\n").filter(Boolean);
    for (const line of lines) {
      try {
        const o = JSON.parse(line) as { _kind?: string; lead_id?: string };
        if (o._kind === "webhook_result" && o.lead_id === leadId) {
          const wr = o as LeadWebhookResultLine;
          row.webhook_ok = wr.ok;
          row.webhook_at = wr.at;
          row.webhook_error = wr.error;
          row.status = wr.ok ? "forwarded" : "failed";
          row.forwarded_at = wr.ok ? wr.at : row.forwarded_at;
        }
      } catch {
        /* skip */
      }
    }
  } catch {
    /* keep base row */
  }
  return row;
}

export async function dispatchLeadWebhook(
  url: string,
  body: LeadOutboundPayloadV1,
  attempts = 3,
): Promise<{ ok: true } | { ok: false; error: string }> {
  let lastErr = "unknown";
  for (let i = 0; i < attempts; i++) {
    try {
      const controller = new AbortController();
      const t = setTimeout(() => controller.abort(), 20_000);
      const r = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(process.env.LEAD_INBOUND_WEBHOOK_SECRET?.trim()
            ? {
                Authorization: `Bearer ${process.env.LEAD_INBOUND_WEBHOOK_SECRET.trim()}`,
              }
            : {}),
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      clearTimeout(t);
      if (r.ok) {
        return { ok: true };
      }
      lastErr = `http_${r.status}`;
    } catch (e) {
      lastErr = e instanceof Error ? e.message : String(e);
    }
    if (i < attempts - 1) {
      await new Promise((res) => setTimeout(res, 1000 * (i + 1)));
    }
  }
  return { ok: false, error: lastErr };
}
