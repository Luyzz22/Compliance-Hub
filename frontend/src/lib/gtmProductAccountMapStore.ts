import { mkdir, readFile, writeFile } from "fs/promises";
import { dirname, join } from "path";

import { extractEmailDomain } from "@/lib/leadIdentity";
import type { LeadInboxItem } from "@/lib/leadInboxTypes";

export type GtmProductMapEntry = {
  tenant_id: string;
  /** Normalisierte Domain (z. B. acme.de), optional wenn account_key gesetzt. */
  domain?: string;
  /** Exakter lead_account_key (ac_v1_dom_* / ac_v1_co_*). */
  account_key?: string;
  /** Anzeige für Admins. */
  label?: string;
  /** Expliziter Pilot-Hinweis im Mapping (informativ). */
  pilot?: boolean;
};

export type GtmProductAccountMapState = {
  entries: GtmProductMapEntry[];
};

function resolvePath(): string {
  const fromEnv = process.env.GTM_PRODUCT_ACCOUNT_MAP_PATH?.trim();
  if (fromEnv) return fromEnv;
  if (process.env.VERCEL) {
    return join("/tmp", "compliancehub-gtm-product-account-map.json");
  }
  return join(process.cwd(), "data", "gtm-product-account-map.json");
}

function normalizeDomain(d: string): string {
  return d.trim().toLowerCase().replace(/^@+/, "");
}

function emptyState(): GtmProductAccountMapState {
  return { entries: [] };
}

export async function readGtmProductAccountMap(): Promise<GtmProductAccountMapState> {
  const path = resolvePath();
  try {
    const raw = await readFile(path, "utf8");
    const o = JSON.parse(raw) as { entries?: unknown };
    if (!o || typeof o !== "object") return emptyState();
    const entries: GtmProductMapEntry[] = [];
    if (Array.isArray(o.entries)) {
      for (const e of o.entries) {
        if (!e || typeof e !== "object") continue;
        const rec = e as Record<string, unknown>;
        const tenant_id = typeof rec.tenant_id === "string" ? rec.tenant_id.trim() : "";
        if (!tenant_id) continue;
        const domain = typeof rec.domain === "string" ? normalizeDomain(rec.domain) : undefined;
        const account_key =
          typeof rec.account_key === "string" ? rec.account_key.trim() : undefined;
        const label = typeof rec.label === "string" ? rec.label.trim() : undefined;
        const pilot = rec.pilot === true;
        if (!domain && !account_key) continue;
        entries.push({
          tenant_id,
          domain: domain || undefined,
          account_key: account_key || undefined,
          label: label || undefined,
          pilot,
        });
      }
    }
    return { entries };
  } catch {
    return emptyState();
  }
}

/** Findet erste passende Map-Zeile: account_key schlägt Domain aus E-Mail. */
export function findGtmProductMapEntry(
  map: GtmProductAccountMapState,
  lead: Pick<LeadInboxItem, "lead_account_key" | "business_email">,
): GtmProductMapEntry | null {
  const ak = lead.lead_account_key?.trim() || null;
  if (ak) {
    for (const e of map.entries) {
      if (e.account_key && e.account_key === ak) return e;
    }
  }
  const dom = extractEmailDomain(lead.business_email);
  if (!dom) return null;
  for (const e of map.entries) {
    if (e.domain && normalizeDomain(e.domain) === dom) return e;
  }
  return null;
}

export async function writeGtmProductAccountMap(state: GtmProductAccountMapState): Promise<void> {
  const path = resolvePath();
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, `${JSON.stringify({ entries: state.entries }, null, 2)}\n`, "utf8");
}
