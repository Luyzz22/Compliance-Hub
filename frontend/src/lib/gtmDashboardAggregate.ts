import "server-only";

import {
  isoInWindow,
  MS_PER_DAY,
  utcDayKeyFromMs,
  utcWeekStartMondayFromMs,
  windowBoundsMs,
} from "@/lib/gtmDashboardTime";
import { attachContactRollups, mergeLeadsWithOps } from "@/lib/leadInboxMerge";
import type { LeadInboxItem } from "@/lib/leadInboxTypes";
import { readLeadOpsState } from "@/lib/leadOpsState";
import { readAllLeadRecordsMerged } from "@/lib/leadPersistence";
import { listAllLeadSyncJobs } from "@/lib/leadSyncStore";
import type { LeadAttributionSource } from "@/lib/leadAttribution";
import { LEAD_ATTRIBUTION_SOURCE_LABELS_DE } from "@/lib/leadAttributionLabels";
import { evaluateGtmHealth } from "@/lib/gtmHealthEngine";
import {
  GTM_HEALTH_QUALIFIED_NO_DEAL_DAYS,
  GTM_HEALTH_STUCK_SYNC_HOURS,
  GTM_HEALTH_UNTRIAGED_DAYS,
} from "@/lib/gtmHealthThresholds";
import type {
  GtmAttentionItem,
  GtmAttributionBreakdownRow,
  GtmDailyPoint,
  GtmDashboardSnapshot,
  GtmFunnelStage,
  GtmSegmentBucket,
  GtmWeeklyPoint,
  GtmWindowMetrics,
} from "@/lib/gtmDashboardTypes";
import type { LeadSyncJob, LeadSyncTarget } from "@/lib/leadSyncTypes";

export type { GtmWindowKey } from "@/lib/gtmDashboardTime";
export type {
  GtmAttentionItem,
  GtmAttributionBreakdownRow,
  GtmAttributionHealthRow,
  GtmDailyPoint,
  GtmDashboardSnapshot,
  GtmFunnelStage,
  GtmHealthLayer,
  GtmHealthStatus,
  GtmHealthTile,
  GtmOpsHint,
  GtmSegmentBucket,
  GtmSegmentReadinessRow,
  GtmWeeklyPoint,
  GtmWindowMetrics,
} from "@/lib/gtmDashboardTypes";

function segmentBucket(seg: string): GtmSegmentBucket {
  if (seg === "industrie_mittelstand") return "industrie_mittelstand";
  if (seg === "kanzlei_wp") return "kanzlei_wp";
  if (seg === "enterprise_sap") return "enterprise_sap";
  return "other";
}

const SEGMENT_LABELS_DE: Record<GtmSegmentBucket, string> = {
  industrie_mittelstand: "Industrie / Mittelstand",
  kanzlei_wp: "Kanzlei / WP",
  enterprise_sap: "Enterprise / SAP",
  other: "Sonstiges",
};

function isQualifiedTriage(t: LeadInboxItem["triage_status"]): boolean {
  return t === "qualified" || t === "closed_won_interest";
}

function isContactedOrBeyond(t: LeadInboxItem["triage_status"]): boolean {
  return (
    t === "contacted" ||
    t === "qualified" ||
    t === "closed_won_interest" ||
    t === "closed_not_now"
  );
}

function emptySegmentCounts(): Record<GtmSegmentBucket, { inquiries: number; qualified: number }> {
  return {
    industrie_mittelstand: { inquiries: 0, qualified: 0 },
    kanzlei_wp: { inquiries: 0, qualified: 0 },
    enterprise_sap: { inquiries: 0, qualified: 0 },
    other: { inquiries: 0, qualified: 0 },
  };
}

function jobTimestampForStatus(j: LeadSyncJob): string {
  return j.updated_at ?? j.last_attempt_at ?? j.created_at;
}

function isHubspotSyncedJob(j: LeadSyncJob, startMs: number, endMs: number): boolean {
  if (j.target !== "hubspot" || j.status !== "sent") return false;
  return isoInWindow(jobTimestampForStatus(j), startMs, endMs);
}

function isDeadLetterInWindow(j: LeadSyncJob, startMs: number, endMs: number): boolean {
  if (j.status !== "dead_letter") return false;
  return isoInWindow(jobTimestampForStatus(j), startMs, endMs);
}

function isPipedriveDealCreatedJob(j: LeadSyncJob): boolean {
  if (j.target !== "pipedrive" || j.status !== "sent") return false;
  const m = j.mock_result;
  if (!m || typeof m !== "object") return false;
  const o = m as Record<string, unknown>;
  return o.system === "pipedrive" && o.deal_action === "created";
}

function pipedriveDealCreatedAt(j: LeadSyncJob): string {
  const m = j.mock_result as Record<string, unknown> | undefined;
  return typeof m?.synced_at === "string" ? m.synced_at : jobTimestampForStatus(j);
}

function pipedriveDealCreatedInWindow(j: LeadSyncJob, startMs: number, endMs: number): boolean {
  if (!isPipedriveDealCreatedJob(j)) return false;
  return isoInWindow(pipedriveDealCreatedAt(j), startMs, endMs);
}

function syncJobBad(j: LeadSyncJob): boolean {
  return j.status === "failed" || j.status === "dead_letter";
}

function isCrmTarget(t: LeadSyncTarget): boolean {
  return t === "hubspot" || t === "pipedrive";
}

/** Nur echte Connectors (keine Stubs) für Health-Zähler. */
function isProductionCrmTarget(t: LeadSyncTarget): boolean {
  return t === "hubspot" || t === "pipedrive";
}

function isPipedriveSentInWindow(j: LeadSyncJob, startMs: number, endMs: number): boolean {
  if (j.target !== "pipedrive" || j.status !== "sent") return false;
  return isoInWindow(jobTimestampForStatus(j), startMs, endMs);
}

export async function computeGtmDashboardSnapshot(now: Date = new Date()): Promise<GtmDashboardSnapshot> {
  const nowMs = now.getTime();
  const w7 = windowBoundsMs(7, nowMs);
  const w30 = windowBoundsMs(30, nowMs);

  const allRows = await readAllLeadRecordsMerged();
  const ops = await readLeadOpsState();
  const merged = mergeLeadsWithOps(allRows, ops);
  const items = attachContactRollups(merged, allRows, ops);
  const jobs = await listAllLeadSyncJobs();

  const leadIdToSegment = new Map<string, GtmSegmentBucket>();
  for (const it of items) {
    leadIdToSegment.set(it.lead_id, segmentBucket(it.segment));
  }

  const syncIssuesBySegment: Record<GtmSegmentBucket, number> = {
    industrie_mittelstand: 0,
    kanzlei_wp: 0,
    enterprise_sap: 0,
    other: 0,
  };

  for (const j of jobs) {
    if (!syncJobBad(j) || !isCrmTarget(j.target)) continue;
    const ts = jobTimestampForStatus(j);
    if (!isoInWindow(ts, w30.start, w30.end)) continue;
    const seg = leadIdToSegment.get(j.lead_id) ?? "other";
    syncIssuesBySegment[seg] += 1;
  }

  function metricsForWindow(startMs: number, endMs: number): GtmWindowMetrics {
    const inW = (iso: string) => isoInWindow(iso, startMs, endMs);
    const windowItems = items.filter((it) => inW(it.created_at));

    const bySeg = emptySegmentCounts();
    let repeated = 0;
    let qualified = 0;
    let contacted = 0;
    let failedWh = 0;

    for (const it of windowItems) {
      const b = segmentBucket(it.segment);
      bySeg[b].inquiries += 1;
      if (isQualifiedTriage(it.triage_status)) {
        qualified += 1;
        bySeg[b].qualified += 1;
      }
      if (it.contact_submission_count > 1) repeated += 1;
      if (it.triage_status === "contacted") contacted += 1;
      if (it.forwarding_status === "failed") failedWh += 1;
    }

    let deadLetter = 0;
    let hubspotSent = 0;
    let pdCreated = 0;
    for (const j of jobs) {
      if (isDeadLetterInWindow(j, startMs, endMs)) deadLetter += 1;
      if (isHubspotSyncedJob(j, startMs, endMs)) hubspotSent += 1;
      if (pipedriveDealCreatedInWindow(j, startMs, endMs)) pdCreated += 1;
    }

    return {
      inbound_inquiries: windowItems.length,
      repeated_contact_inquiries: repeated,
      qualified_leads: qualified,
      contacted_leads: contacted,
      failed_webhook_forwards: failedWh,
      dead_letter_sync_jobs: deadLetter,
      hubspot_synced_jobs: hubspotSent,
      pipedrive_deals_created: pdCreated,
      by_segment: bySeg,
    };
  }

  const kpis: GtmDashboardSnapshot["kpis"] = {
    "7d": metricsForWindow(w7.start, w7.end),
    "30d": metricsForWindow(w30.start, w30.end),
  };

  function funnelCount(
    startMs: number,
    endMs: number,
    pred: (it: LeadInboxItem) => boolean,
  ): number {
    return items.filter((it) => isoInWindow(it.created_at, startMs, endMs) && pred(it)).length;
  }

  const funnel: GtmFunnelStage[] = [
    {
      id: "cta",
      label_de: "CTA-Klicks (Homepage)",
      counts: { "7d": 0, "30d": 0 },
    },
    {
      id: "submissions",
      label_de: "Kontaktanfragen (Formular)",
      counts: {
        "7d": funnelCount(w7.start, w7.end, () => true),
        "30d": funnelCount(w30.start, w30.end, () => true),
      },
    },
    {
      id: "triaged",
      label_de: "Triage gestartet (nicht mehr „Neu“)",
      counts: {
        "7d": funnelCount(w7.start, w7.end, (it) => it.triage_status !== "received"),
        "30d": funnelCount(w30.start, w30.end, (it) => it.triage_status !== "received"),
      },
    },
    {
      id: "contacted_funnel",
      label_de: "Kontaktiert oder weiter (Pipeline)",
      counts: {
        "7d": funnelCount(w7.start, w7.end, (it) => isContactedOrBeyond(it.triage_status)),
        "30d": funnelCount(w30.start, w30.end, (it) => isContactedOrBeyond(it.triage_status)),
      },
    },
    {
      id: "qualified_funnel",
      label_de: "Qualifiziert / Abschluss-Interesse",
      counts: {
        "7d": funnelCount(w7.start, w7.end, (it) => isQualifiedTriage(it.triage_status)),
        "30d": funnelCount(w30.start, w30.end, (it) => isQualifiedTriage(it.triage_status)),
      },
    },
    {
      id: "pipedrive_deals",
      label_de: "Pipedrive-Deals neu angelegt (Sync)",
      counts: {
        "7d": kpis["7d"].pipedrive_deals_created,
        "30d": kpis["30d"].pipedrive_deals_created,
      },
    },
  ];

  const segment_table: GtmDashboardSnapshot["segment_table"] = (
    [
      "industrie_mittelstand",
      "kanzlei_wp",
      "enterprise_sap",
      "other",
    ] as const
  ).map((segment) => ({
    segment,
    label_de: SEGMENT_LABELS_DE[segment],
    inquiries_30d: kpis["30d"].by_segment[segment].inquiries,
    qualified_30d: kpis["30d"].by_segment[segment].qualified,
    sync_issues_30d: syncIssuesBySegment[segment],
  }));

  const webhookFails = items
    .filter((it) => it.forwarding_status === "failed")
    .sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))
    .slice(0, 8)
    .map(
      (it): GtmAttentionItem => ({
        kind: "failed_webhook",
        lead_id: it.lead_id,
        detail: it.webhook_error?.slice(0, 120),
        at: it.created_at,
      }),
    );

  const deadLetterItems = jobs
    .filter((j) => j.status === "dead_letter")
    .sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at))
    .slice(0, 8)
    .map(
      (j): GtmAttentionItem => ({
        kind: "dead_letter_sync",
        lead_id: j.lead_id,
        job_id: j.job_id,
        target: j.target,
        detail: j.last_error?.slice(0, 160),
        at: j.updated_at,
      }),
    );

  const repeatItems = items
    .filter(
      (it) =>
        it.contact_submission_count > 1 &&
        it.triage_status === "received" &&
        it.duplicate_hint === "same_email_repeat",
    )
    .sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))
    .slice(0, 8)
    .map(
      (it): GtmAttentionItem => ({
        kind: "unresolved_repeat_contact",
        lead_id: it.lead_id,
        detail: `×${it.contact_submission_count} · ${it.segment}`,
        at: it.created_at,
      }),
    );

  const crmSyncFails = [...jobs]
    .filter((j) => syncJobBad(j) && isCrmTarget(j.target))
    .sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at))
    .slice(0, 8)
    .map(
      (j): GtmAttentionItem => ({
        kind: "crm_sync_failed",
        lead_id: j.lead_id,
        job_id: j.job_id,
        target: j.target,
        detail: j.last_error?.slice(0, 120),
        at: j.updated_at,
      }),
    );

  const attentionMerged: GtmAttentionItem[] = [
    ...webhookFails,
    ...deadLetterItems,
    ...repeatItems,
    ...crmSyncFails,
  ].slice(0, 28);

  /* Tagesreihe: letzte 14 Tage UTC, alle Anfragen nach created_at */
  const daily: GtmDailyPoint[] = [];
  for (let i = 13; i >= 0; i--) {
    const dayMs = nowMs - i * MS_PER_DAY;
    const key = utcDayKeyFromMs(dayMs);
    const count = items.filter((it) => utcDayKeyFromMs(Date.parse(it.created_at)) === key).length;
    daily.push({ day: key, inquiries: count });
  }

  /* Wochen: letzte 8 Wochen — qualifiziert nach created_at, Deals nach synced_at */
  const weekKeys: string[] = [];
  for (let w = 7; w >= 0; w--) {
    weekKeys.push(utcWeekStartMondayFromMs(nowMs - w * 7 * MS_PER_DAY));
  }
  const uniqWeeks = [...new Set(weekKeys)].sort();

  const qualifiedPerWeek = new Map<string, number>();
  for (const wk of uniqWeeks) qualifiedPerWeek.set(wk, 0);
  for (const it of items) {
    if (!isQualifiedTriage(it.triage_status)) continue;
    const wk = utcWeekStartMondayFromMs(Date.parse(it.created_at));
    if (qualifiedPerWeek.has(wk)) qualifiedPerWeek.set(wk, (qualifiedPerWeek.get(wk) ?? 0) + 1);
  }

  const dealsPerWeek = new Map<string, number>();
  for (const wk of uniqWeeks) dealsPerWeek.set(wk, 0);
  for (const j of jobs) {
    if (!isPipedriveDealCreatedJob(j)) continue;
    const at = pipedriveDealCreatedAt(j);
    const wk = utcWeekStartMondayFromMs(Date.parse(at));
    if (dealsPerWeek.has(wk)) dealsPerWeek.set(wk, (dealsPerWeek.get(wk) ?? 0) + 1);
  }

  const qualified_and_deals_per_week_utc: GtmWeeklyPoint[] = uniqWeeks.map((week_start) => ({
    week_start,
    qualified: qualifiedPerWeek.get(week_start) ?? 0,
    pipedrive_deals_created: dealsPerWeek.get(week_start) ?? 0,
  }));

  type Agg = { inquiries: number; qualified: number; deals: number };
  function bumpAgg(m: Map<string, Agg>, key: string, qualified: boolean, deal: boolean) {
    const cur = m.get(key) ?? { inquiries: 0, qualified: 0, deals: 0 };
    cur.inquiries += 1;
    if (qualified) cur.qualified += 1;
    if (deal) cur.deals += 1;
    m.set(key, cur);
  }

  const leadDeal30d = new Set<string>();
  for (const j of jobs) {
    if (pipedriveDealCreatedInWindow(j, w30.start, w30.end)) leadDeal30d.add(j.lead_id);
  }

  const items30d = items.filter((it) => isoInWindow(it.created_at, w30.start, w30.end));
  const bySource = new Map<string, Agg>();
  const byCampaign = new Map<string, Agg>();
  for (const it of items30d) {
    const q = isQualifiedTriage(it.triage_status);
    const deal = leadDeal30d.has(it.lead_id);
    bumpAgg(bySource, it.attribution_source, q, deal);
    const camp = it.attribution_campaign || "(ohne_campaign)";
    bumpAgg(byCampaign, camp, q, deal);
  }

  function rowsFromMap(
    m: Map<string, Agg>,
    labelForKey: (k: string) => string,
  ): GtmAttributionBreakdownRow[] {
    return [...m.entries()]
      .sort((a, b) => b[1].inquiries - a[1].inquiries)
      .slice(0, 14)
      .map(([key, v]) => ({
        key,
        label_de: labelForKey(key),
        inquiries_30d: v.inquiries,
        qualified_30d: v.qualified,
        pipedrive_deals_created_30d: v.deals,
      }));
  }

  const attribution_by_source_30d = rowsFromMap(bySource, (k) => {
    const label = LEAD_ATTRIBUTION_SOURCE_LABELS_DE[k as LeadAttributionSource];
    return label ?? k;
  });

  const attribution_by_campaign_30d = rowsFromMap(byCampaign, (k) =>
    k === "(ohne_campaign)" ? "Ohne utm_campaign" : k,
  );

  const MS_UNTRIAGED = GTM_HEALTH_UNTRIAGED_DAYS * MS_PER_DAY;
  const MS_QUAL_NO_DEAL = GTM_HEALTH_QUALIFIED_NO_DEAL_DAYS * MS_PER_DAY;
  const MS_STUCK_SYNC = GTM_HEALTH_STUCK_SYNC_HOURS * 60 * 60 * 1000;

  const spam_30d = items30d.filter((it) => it.triage_status === "spam").length;

  const untriaged_over_3d = items.filter((it) => {
    if (it.triage_status !== "received") return false;
    const age = nowMs - Date.parse(it.created_at);
    return age > MS_UNTRIAGED;
  }).length;

  let crm_dead_letter_30d = 0;
  let crm_failed_30d = 0;
  let crm_sent_ok_30d = 0;
  for (const j of jobs) {
    if (!isProductionCrmTarget(j.target)) continue;
    const ts = jobTimestampForStatus(j);
    if (!isoInWindow(ts, w30.start, w30.end)) continue;
    if (j.status === "dead_letter") crm_dead_letter_30d += 1;
    else if (j.status === "failed") crm_failed_30d += 1;
    else if (j.status === "sent") crm_sent_ok_30d += 1;
  }

  let stuck_failed_crm_sync_24h = 0;
  for (const j of jobs) {
    if (!isProductionCrmTarget(j.target) || j.status !== "failed") continue;
    const last = Date.parse(j.last_attempt_at ?? j.updated_at);
    if (Number.isFinite(last) && nowMs - last > MS_STUCK_SYNC) stuck_failed_crm_sync_24h += 1;
  }

  const leadIdHasPipedriveDeal = new Set<string>();
  for (const j of jobs) {
    if (isPipedriveDealCreatedJob(j)) leadIdHasPipedriveDeal.add(j.lead_id);
  }

  const qualified_no_pipedrive_deal_old_7d = items.filter((it) => {
    if (!isQualifiedTriage(it.triage_status)) return false;
    if (leadIdHasPipedriveDeal.has(it.lead_id)) return false;
    const age = nowMs - Date.parse(it.created_at);
    return age > MS_QUAL_NO_DEAL;
  }).length;

  const hubspotBySegment: Record<GtmSegmentBucket, number> = {
    industrie_mittelstand: 0,
    kanzlei_wp: 0,
    enterprise_sap: 0,
    other: 0,
  };
  const pipedriveTouchBySegment: Record<GtmSegmentBucket, number> = {
    industrie_mittelstand: 0,
    kanzlei_wp: 0,
    enterprise_sap: 0,
    other: 0,
  };
  for (const j of jobs) {
    if (!isoInWindow(jobTimestampForStatus(j), w30.start, w30.end)) continue;
    const seg = leadIdToSegment.get(j.lead_id) ?? "other";
    if (j.target === "hubspot" && j.status === "sent") hubspotBySegment[seg] += 1;
    if (isPipedriveSentInWindow(j, w30.start, w30.end)) pipedriveTouchBySegment[seg] += 1;
  }

  function dominantSourcesForSegment(seg: GtmSegmentBucket): string {
    const counts = new Map<string, number>();
    for (const it of items30d) {
      if (segmentBucket(it.segment) !== seg) continue;
      const k = it.attribution_source;
      counts.set(k, (counts.get(k) ?? 0) + 1);
    }
    const top = [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 2);
    if (top.length === 0) return "—";
    return top
      .map(([k, n]) => `${LEAD_ATTRIBUTION_SOURCE_LABELS_DE[k as LeadAttributionSource] ?? k} (${n})`)
      .join(", ");
  }

  const segmentKeys: GtmSegmentBucket[] = [
    "industrie_mittelstand",
    "kanzlei_wp",
    "enterprise_sap",
    "other",
  ];
  const healthSegments = segmentKeys.map((segment) => ({
    segment,
    label_de: SEGMENT_LABELS_DE[segment],
    inquiries_30d: kpis["30d"].by_segment[segment].inquiries,
    qualified_30d: kpis["30d"].by_segment[segment].qualified,
    hubspot_sent_30d: hubspotBySegment[segment],
    pipedrive_touch_30d: pipedriveTouchBySegment[segment],
    dominant_sources_de: dominantSourcesForSegment(segment),
  }));

  const health = evaluateGtmHealth({
    inbound_30d: kpis["30d"].inbound_inquiries,
    webhook_failed_30d: kpis["30d"].failed_webhook_forwards,
    spam_30d,
    untriaged_over_3d,
    crm_dead_letter_30d,
    crm_failed_30d,
    crm_sent_ok_30d,
    qualified_30d: kpis["30d"].qualified_leads,
    deals_created_30d: kpis["30d"].pipedrive_deals_created,
    stuck_failed_crm_sync_24h,
    qualified_no_pipedrive_deal_old_7d,
    segments: healthSegments,
    attribution_top_sources: attribution_by_source_30d,
  });

  return {
    generated_at: now.toISOString(),
    windows: {
      "7d": { start: new Date(w7.start).toISOString(), end: new Date(w7.end).toISOString() },
      "30d": { start: new Date(w30.start).toISOString(), end: new Date(w30.end).toISOString() },
    },
    kpis,
    funnel,
    segment_table,
    attention: attentionMerged,
    trends: {
      inquiries_per_day_utc: daily,
      qualified_and_deals_per_week_utc: qualified_and_deals_per_week_utc,
    },
    attribution_by_source_30d,
    attribution_by_campaign_30d,
    health,
    data_notes: {
      cta_clicks_persisted: false,
      cta_note_de:
        "CTA-Klicks werden aktuell nur serverseitig geloggt ([marketing-event]), nicht in einem Query-Store — daher keine zuverlässige Zahl im Dashboard.",
      funnel_note_de:
        "Stufen sind absolute Mengen je Zeitraum (Einreichungsdatum). Spätere Stufen können größer wirken als frühere, wenn Leads außerhalb des Fensters qualifiziert wurden; für Steuerung die KPI-Karten und Segmenttabelle nutzen.",
      attribution_note_de:
        "Attribution: first-touch-UTM (Tab-Session) plus Server-Referer-Heuristik beim Absenden — keine Multi-Touch-Zuordnung. „Deals“ = Pipedrive-Sync mit deal_action created im 30-Tage-Fenster.",
      health_note_de:
        "Health ist regelbasiert (Schwellen in gtmHealthThresholds.ts) — kein Board-BI. „Qualifiziert ohne Deal“ nutzt Einreichungsalter statt echtem Qualifizierungszeitpunkt.",
    },
  };
}
