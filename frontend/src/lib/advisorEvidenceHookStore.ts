import "server-only";

import { readFile } from "fs/promises";
import { join } from "path";

import type { EvidenceHookStoredRecord, EvidenceSourceSystemType } from "@/lib/advisorEvidenceHookTypes";

function hooksPath(): string {
  const fromEnv = process.env.ADVISOR_EVIDENCE_HOOKS_PATH?.trim();
  if (fromEnv) return fromEnv;
  if (process.env.VERCEL) return join("/tmp", "compliancehub-advisor-evidence-hooks.json");
  return join(process.cwd(), "data", "advisor-evidence-hooks.json");
}

const SOURCE_TYPES: EvidenceSourceSystemType[] = [
  "sap_s4hana",
  "sap_btp",
  "datev",
  "ms_dynamics",
  "generic_erp",
];

function isSourceType(s: string): s is EvidenceSourceSystemType {
  return SOURCE_TYPES.includes(s as EvidenceSourceSystemType);
}

const DOMAINS = [
  "invoice",
  "access",
  "approval",
  "vendor",
  "ai_system_inventory",
  "policy_artifact",
] as const;

function isDomain(s: string): s is EvidenceHookStoredRecord["evidence_domain"] {
  return (DOMAINS as readonly string[]).includes(s);
}

const STATUSES: EvidenceHookStoredRecord["connection_status"][] = [
  "not_connected",
  "planned",
  "connected",
  "error",
];

function isStatus(s: string): s is EvidenceHookStoredRecord["connection_status"] {
  return STATUSES.includes(s as EvidenceHookStoredRecord["connection_status"]);
}

export type AdvisorEvidenceHooksFile = { version?: string; hooks?: unknown };

export async function readAdvisorEvidenceHooks(): Promise<EvidenceHookStoredRecord[]> {
  const path = hooksPath();
  try {
    const raw = await readFile(path, "utf8");
    const o = JSON.parse(raw) as AdvisorEvidenceHooksFile;
    if (!o || typeof o !== "object" || !Array.isArray(o.hooks)) return [];
    const out: EvidenceHookStoredRecord[] = [];
    for (const e of o.hooks) {
      if (!e || typeof e !== "object") continue;
      const r = e as Record<string, unknown>;
      if (typeof r.hook_id !== "string" || !r.hook_id.trim()) continue;
      if (typeof r.tenant_id !== "string" || !r.tenant_id.trim()) continue;
      if (typeof r.source_system_type !== "string" || !isSourceType(r.source_system_type)) continue;
      if (typeof r.source_label !== "string" || !r.source_label.trim()) continue;
      if (typeof r.evidence_domain !== "string" || !isDomain(r.evidence_domain)) continue;
      if (typeof r.connection_status !== "string" || !isStatus(r.connection_status)) continue;
      const last_sync_at =
        r.last_sync_at == null ? null : typeof r.last_sync_at === "string" ? r.last_sync_at : null;
      const note = r.note == null ? null : typeof r.note === "string" ? r.note : null;
      out.push({
        hook_id: r.hook_id.trim(),
        tenant_id: r.tenant_id.trim(),
        source_system_type: r.source_system_type,
        source_label: r.source_label.trim(),
        evidence_domain: r.evidence_domain,
        connection_status: r.connection_status,
        last_sync_at,
        note,
      });
    }
    return out;
  } catch {
    return [];
  }
}
