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
import type {
  GtmAttentionItem,
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
  GtmDailyPoint,
  GtmDashboardSnapshot,
  GtmFunnelStage,
  GtmSegmentBucket,
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
    data_notes: {
      cta_clicks_persisted: false,
      cta_note_de:
        "CTA-Klicks werden aktuell nur serverseitig geloggt ([marketing-event]), nicht in einem Query-Store — daher keine zuverlässige Zahl im Dashboard.",
      funnel_note_de:
        "Stufen sind absolute Mengen je Zeitraum (Einreichungsdatum). Spätere Stufen können größer wirken als frühere, wenn Leads außerhalb des Fensters qualifiziert wurden; für Steuerung die KPI-Karten und Segmenttabelle nutzen.",
    },
  };
}
