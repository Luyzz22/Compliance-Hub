import "server-only";

import {
  classifyMappedTenantReadiness,
  type GtmGovernanceSignalsInput,
  type GtmReadinessClass,
} from "@/lib/gtmAccountReadiness";
import { isoInWindow, windowBoundsMs } from "@/lib/gtmDashboardTime";
import type { GtmSegmentBucket } from "@/lib/gtmDashboardTypes";
import type {
  GtmProductBridgeHint,
  GtmProductBridgePayload,
  GtmProductBridgeSegmentOverlayRow,
} from "@/lib/gtmProductBridgeTypes";
import { attachContactRollups, mergeLeadsWithOps } from "@/lib/leadInboxMerge";
import type { LeadInboxItem } from "@/lib/leadInboxTypes";
import { readLeadOpsState } from "@/lib/leadOpsState";
import { readAllLeadRecordsMerged } from "@/lib/leadPersistence";
import { listAllLeadSyncJobs } from "@/lib/leadSyncStore";
import {
  findGtmProductMapEntry,
  readGtmProductAccountMap,
  type GtmProductMapEntry,
} from "@/lib/gtmProductAccountMapStore";
import { fetchTenantGovernanceSnapshot } from "@/lib/gtmProductGovernanceFetch";
import type { LeadSyncJob } from "@/lib/leadSyncTypes";

const SEGMENT_LABELS_DE: Record<GtmSegmentBucket, string> = {
  industrie_mittelstand: "Industrie / Mittelstand",
  kanzlei_wp: "Kanzlei / WP",
  enterprise_sap: "Enterprise / SAP",
  other: "Sonstiges",
};

function segmentBucket(seg: string): GtmSegmentBucket {
  if (seg === "industrie_mittelstand") return "industrie_mittelstand";
  if (seg === "kanzlei_wp") return "kanzlei_wp";
  if (seg === "enterprise_sap") return "enterprise_sap";
  return "other";
}

function emptyMatrix(): Record<GtmReadinessClass, Record<GtmSegmentBucket, number>> {
  return {
    no_footprint: {
      industrie_mittelstand: 0,
      kanzlei_wp: 0,
      enterprise_sap: 0,
      other: 0,
    },
    early_pilot: {
      industrie_mittelstand: 0,
      kanzlei_wp: 0,
      enterprise_sap: 0,
      other: 0,
    },
    baseline_governance: {
      industrie_mittelstand: 0,
      kanzlei_wp: 0,
      enterprise_sap: 0,
      other: 0,
    },
    advanced_governance: {
      industrie_mittelstand: 0,
      kanzlei_wp: 0,
      enterprise_sap: 0,
      other: 0,
    },
  };
}

function countPipedriveDealsCreated30dForLead(
  leadId: string,
  jobs: LeadSyncJob[],
  startMs: number,
  endMs: number,
): number {
  for (const j of jobs) {
    if (j.lead_id !== leadId) continue;
    if (j.target !== "pipedrive" || j.status !== "sent") continue;
    const m = j.mock_result;
    if (!m || typeof m !== "object") continue;
    const o = m as Record<string, unknown>;
    if (o.system !== "pipedrive" || o.deal_action !== "created") continue;
    const ts =
      typeof o.synced_at === "string"
        ? o.synced_at
        : j.updated_at ?? j.last_attempt_at ?? j.created_at;
    if (isoInWindow(ts, startMs, endMs)) return 1;
  }
  return 0;
}

async function loadLeadsAndJobs(): Promise<{
  items: LeadInboxItem[];
  jobs: LeadSyncJob[];
}> {
  const allRows = await readAllLeadRecordsMerged();
  const ops = await readLeadOpsState();
  const merged = mergeLeadsWithOps(allRows, ops);
  const items = attachContactRollups(merged, allRows, ops);
  const jobs = await listAllLeadSyncJobs();
  return { items, jobs };
}

function signalsToInput(
  snap: Awaited<ReturnType<typeof fetchTenantGovernanceSnapshot>>,
  pilot_flag: boolean,
): GtmGovernanceSignalsInput {
  return {
    ai_systems_count: snap.ai_systems_count,
    progress_steps: snap.progress_steps,
    active_frameworks: snap.active_frameworks,
    fetch_ok: snap.fetch_ok,
    pilot_flag,
  };
}

export async function computeProductBridgePayload(now: Date = new Date()): Promise<GtmProductBridgePayload> {
  const map = await readGtmProductAccountMap();
  const { items, jobs } = await loadLeadsAndJobs();
  const nowMs = now.getTime();
  const w30 = windowBoundsMs(30, nowMs);

  const tenantIds = new Set<string>();
  for (const e of map.entries) {
    tenantIds.add(e.tenant_id);
  }

  const cache = new Map<string, Awaited<ReturnType<typeof fetchTenantGovernanceSnapshot>>>();
  let backendReachable = false;

  for (const tid of tenantIds) {
    const snap = await fetchTenantGovernanceSnapshot(tid);
    cache.set(tid, snap);
    if (snap.fetch_ok) backendReachable = true;
  }

  const matrix = emptyMatrix();
  const overlayAgg: Record<
    GtmSegmentBucket,
    {
      inquiries: number;
      qualified: number;
      deals: number;
      byClass: Record<GtmReadinessClass, number>;
    }
  > = {
    industrie_mittelstand: {
      inquiries: 0,
      qualified: 0,
      deals: 0,
      byClass: { no_footprint: 0, early_pilot: 0, baseline_governance: 0, advanced_governance: 0 },
    },
    kanzlei_wp: {
      inquiries: 0,
      qualified: 0,
      deals: 0,
      byClass: { no_footprint: 0, early_pilot: 0, baseline_governance: 0, advanced_governance: 0 },
    },
    enterprise_sap: {
      inquiries: 0,
      qualified: 0,
      deals: 0,
      byClass: { no_footprint: 0, early_pilot: 0, baseline_governance: 0, advanced_governance: 0 },
    },
    other: {
      inquiries: 0,
      qualified: 0,
      deals: 0,
      byClass: { no_footprint: 0, early_pilot: 0, baseline_governance: 0, advanced_governance: 0 },
    },
  };

  function classForLead(it: LeadInboxItem): GtmReadinessClass {
    const entry = findGtmProductMapEntry(map, it);
    if (!entry) return "no_footprint";
    const snap = cache.get(entry.tenant_id);
    if (!snap) return "early_pilot";
    return classifyMappedTenantReadiness(signalsToInput(snap, entry.pilot === true));
  }

  for (const it of items) {
    if (!isoInWindow(it.created_at, w30.start, w30.end)) continue;
    const seg = segmentBucket(it.segment);
    const cls = classForLead(it);
    matrix[cls][seg] += 1;

    const q =
      it.triage_status === "qualified" || it.triage_status === "closed_won_interest" ? 1 : 0;
    const d = countPipedriveDealsCreated30dForLead(it.lead_id, jobs, w30.start, w30.end);

    overlayAgg[seg].inquiries += 1;
    overlayAgg[seg].qualified += q;
    overlayAgg[seg].deals += d;
    overlayAgg[seg].byClass[cls] += 1;
  }

  const rowTotals: Record<GtmReadinessClass, number> = {
    no_footprint: 0,
    early_pilot: 0,
    baseline_governance: 0,
    advanced_governance: 0,
  };
  const colTotals: Record<GtmSegmentBucket, number> = {
    industrie_mittelstand: 0,
    kanzlei_wp: 0,
    enterprise_sap: 0,
    other: 0,
  };

  for (const cls of Object.keys(matrix) as GtmReadinessClass[]) {
    for (const seg of Object.keys(colTotals) as GtmSegmentBucket[]) {
      const c = matrix[cls][seg];
      rowTotals[cls] += c;
      colTotals[seg] += c;
    }
  }

  const columns: GtmSegmentBucket[] = [
    "industrie_mittelstand",
    "kanzlei_wp",
    "enterprise_sap",
    "other",
  ];
  const rows: GtmReadinessClass[] = [
    "no_footprint",
    "early_pilot",
    "baseline_governance",
    "advanced_governance",
  ];

  const segment_overlay: GtmProductBridgeSegmentOverlayRow[] = columns.map((segment) => {
    const agg = overlayAgg[segment];
    let dominant: GtmReadinessClass = "no_footprint";
    let max = -1;
    for (const r of rows) {
      if (agg.byClass[r] > max) {
        max = agg.byClass[r];
        dominant = r;
      }
    }
    if (agg.inquiries === 0) dominant = "no_footprint";
    return {
      segment,
      label_de: SEGMENT_LABELS_DE[segment],
      inquiries_30d: agg.inquiries,
      qualified_30d: agg.qualified,
      pipedrive_deals_created_30d: agg.deals,
      dominant_readiness: dominant,
      readiness_breakdown: { ...agg.byClass },
    };
  });

  return {
    generated_at: now.toISOString(),
    window_days: 30,
    map_entry_count: map.entries.length,
    mapped_tenant_count: tenantIds.size,
    backend_reachable: backendReachable,
    note_de:
      "Brücke: manuelle Zuordnung (Domain/account_key → tenant_id). Unbekannte Leads zählen als „Kein Mandanten-Footprint“. Backend muss für Live-Signale erreichbar sein (COMPLIANCEHUB_API_BASE_URL / KEY).",
    matrix: {
      rows,
      columns,
      column_labels_de: SEGMENT_LABELS_DE,
      cells: matrix,
      row_totals: rowTotals,
      column_totals: colTotals,
    },
    segment_overlay,
  };
}

/** Hinweise für Lead-Detail (GET/PATCH). */
export async function buildProductBridgeHintForLead(
  item: LeadInboxItem,
): Promise<GtmProductBridgeHint> {
  const { GTM_READINESS_LABELS_DE } = await import("@/lib/gtmAccountReadiness");
  const map = await readGtmProductAccountMap();
  const entry: GtmProductMapEntry | null = findGtmProductMapEntry(map, item);

  if (!entry) {
    return {
      mapped: false,
      tenant_id: null,
      map_label: null,
      pilot_flag: false,
      readiness_class: "no_footprint",
      readiness_label_de: GTM_READINESS_LABELS_DE.no_footprint,
      governance_hints_de: [
        "Kein Eintrag in gtm-product-account-map (Domain oder lead_account_key). Nur GTM-Sicht.",
      ],
      backend_reachable: false,
    };
  }

  const snap = await fetchTenantGovernanceSnapshot(entry.tenant_id);
  const cls = classifyMappedTenantReadiness(signalsToInput(snap, entry.pilot === true));

  const hints: string[] = [];
  hints.push(`Gemappt auf Mandant: ${entry.tenant_id}${entry.label ? ` (${entry.label})` : ""}.`);
  if (entry.pilot) hints.push("Mapping markiert explizit als Pilot (organisatorisch).");
  if (!snap.fetch_ok) {
    hints.push("Produkt-API derzeit nicht lesbar – Readiness konservativ als „Pilot / dünn“ gewertet.");
  } else {
    hints.push(
      `KI-Systeme im Inventar (Anzahl): ${snap.ai_systems_count}. Fortschrittsschritte (Wizard/DB): ${snap.progress_steps.length ? snap.progress_steps.join(", ") : "keine"}.`,
    );
    if (snap.progress_steps.includes(6)) {
      hints.push("Board-Report-Spur im Setup erkannt (Schritt 6).");
    } else {
      hints.push("Kein abgeschlossener Board-Report-Schritt (6) in den abgeleiteten Setup-Schritten.");
    }
    if (snap.progress_steps.includes(4)) {
      hints.push("KPI-/Messwert-Register laut Setup begonnen (Schritt 4).");
    }
  }

  return {
    mapped: true,
    tenant_id: entry.tenant_id,
    map_label: entry.label ?? null,
    pilot_flag: entry.pilot === true,
    readiness_class: cls,
    readiness_label_de: GTM_READINESS_LABELS_DE[cls],
    governance_hints_de: hints,
    backend_reachable: snap.fetch_ok,
  };
}
