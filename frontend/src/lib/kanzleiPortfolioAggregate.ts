import "server-only";

import type { AdvisorMandantHistoryEntry } from "@/lib/advisorMandantHistoryStore";
import { readAdvisorMandantHistoryMap } from "@/lib/advisorMandantHistoryStore";
import { attachAdvisorKpiToPayload } from "@/lib/advisorKpiPortfolioAggregate";
import type { AdvisorMandantRemindersState, MandantReminderApiEntry } from "@/lib/advisorMandantReminderTypes";
import {
  readAdvisorMandantRemindersState,
  syncAdvisorMandantRemindersFromPortfolio,
  syncAdvisorSlaEscalationReminders,
} from "@/lib/advisorMandantReminderStore";
import {
  criticalRuleIdsFromFindings,
  evaluateAdvisorSla,
  stubAdvisorSlaEvaluation,
} from "@/lib/advisorSlaEvaluate";
import { readAdvisorSlaSignalState, writeAdvisorSlaSignalState } from "@/lib/advisorSlaSignalStateStore";
import { isDueThisCalendarWeek, isDueTodayOrOverdue } from "@/lib/advisorMandantReminderRules";
import {
  daysSinceValidIso,
  isNonEmptyUnparsableIso,
  maxIsoTimestamps,
} from "@/lib/mandantHistoryMerge";
import type {
  MappedTenantPillarSnapshotBundle,
  TenantPillarSnapshot,
} from "@/lib/boardReadinessAggregate";
import { loadMappedTenantPillarSnapshots } from "@/lib/boardReadinessAggregate";
import { worstTraffic } from "@/lib/boardReadinessThresholds";
import type { BoardReadinessPillarKey, BoardReadinessTraffic } from "@/lib/boardReadinessTypes";
import type { GtmSegmentBucket } from "@/lib/gtmDashboardTypes";
import { GTM_READINESS_LABELS_DE } from "@/lib/gtmAccountReadiness";
import { buildAttentionQueue } from "@/lib/kanzleiAttentionQueue";
import {
  computeGapsHeavyWithoutRecentExport,
  kanzleiAttentionScore,
} from "@/lib/kanzleiPortfolioScoring";
import {
  KANZLEI_PILLAR_LABEL_DE,
  KANZLEI_PORTFOLIO_VERSION,
  type KanzleiPortfolioPayload,
  type KanzleiPortfolioRow,
  type KanzleiAttentionQueueItem,
} from "@/lib/kanzleiPortfolioTypes";
import {
  KANZLEI_ANY_EXPORT_MAX_AGE_DAYS,
  KANZLEI_GAP_HEAVY_FOR_EXPORT_RULE,
  KANZLEI_MANY_OPEN_POINTS,
  KANZLEI_REVIEW_STALE_DAYS,
} from "@/lib/kanzleiReviewCadenceThresholds";
import {
  computeMandantOffenePunkte,
  pillarCodeForOpenPoint,
} from "@/lib/tenantBoardReadinessGaps";

export {
  KANZLEI_ANY_EXPORT_MAX_AGE_DAYS,
  KANZLEI_GAP_HEAVY_FOR_EXPORT_RULE,
  KANZLEI_MANY_OPEN_POINTS,
  KANZLEI_REVIEW_STALE_DAYS,
} from "@/lib/kanzleiReviewCadenceThresholds";

const SEGMENT_LABELS_DE: Record<GtmSegmentBucket, string> = {
  industrie_mittelstand: "Industrie / Mittelstand",
  kanzlei_wp: "Kanzlei / WP",
  enterprise_sap: "Enterprise / SAP",
  other: "Sonstiges",
};

const PILLAR_ORDER: BoardReadinessPillarKey[] = ["eu_ai_act", "iso_42001", "nis2", "dsgvo"];

const PILLAR_KEY_TO_CODE: Record<BoardReadinessPillarKey, string> = {
  eu_ai_act: "EU_AI_Act",
  iso_42001: "ISO_42001",
  nis2: "NIS2",
  dsgvo: "DSGVO",
};

function trafficRank(s: BoardReadinessTraffic): number {
  if (s === "red") return 0;
  if (s === "amber") return 1;
  return 2;
}

function segmentLabel(seg: GtmSegmentBucket | null): string | null {
  if (!seg) return null;
  return SEGMENT_LABELS_DE[seg] ?? null;
}

function worstPillarFromSnapshot(t: TenantPillarSnapshot): {
  key: BoardReadinessPillarKey;
  code: string;
  label_de: string;
} {
  let best: BoardReadinessPillarKey = "eu_ai_act";
  let bestRank = 99;
  for (const key of PILLAR_ORDER) {
    const st =
      key === "eu_ai_act"
        ? t.eu.status
        : key === "iso_42001"
          ? t.iso.status
          : key === "nis2"
            ? t.nis2.status
            : t.dsgvo.status;
    const r = trafficRank(st);
    if (r < bestRank) {
      bestRank = r;
      best = key;
    }
  }
  const code = PILLAR_KEY_TO_CODE[best];
  return { key: best, code, label_de: KANZLEI_PILLAR_LABEL_DE[code] ?? code };
}

const OPEN_PILLAR_PRIORITY = ["EU_AI_Act", "ISO_42001", "NIS2", "DSGVO"] as const;

function weightedTopPillarFromOpenPoints(
  punkte: ReturnType<typeof computeMandantOffenePunkte>,
): { code: string; weight: number } | null {
  const weights: Record<string, number> = {};
  for (const p of punkte) {
    const c = pillarCodeForOpenPoint(p);
    const w = p.dringlichkeit === "hoch" ? 3 : 1;
    weights[c] = (weights[c] ?? 0) + w;
  }
  let bestCode: string | null = null;
  let bestW = 0;
  for (const c of OPEN_PILLAR_PRIORITY) {
    const w = weights[c] ?? 0;
    if (w > bestW) {
      bestW = w;
      bestCode = c;
    }
  }
  if (!bestCode || bestW <= 0) return null;
  return { code: bestCode, weight: bestW };
}

function rowFromSnapshot(
  t: TenantPillarSnapshot,
  nowMs: number,
  historyByTenant: Map<string, AdvisorMandantHistoryEntry>,
): KanzleiPortfolioRow {
  const punkte = computeMandantOffenePunkte(t.tenant_id, t.raw, nowMs);
  const open_points_count = punkte.length;
  const open_points_hoch = punkte.filter((p) => p.dringlichkeit === "hoch").length;

  const weighted = weightedTopPillarFromOpenPoints(punkte);
  const worst = worstPillarFromSnapshot(t);
  const top_gap_pillar_code = weighted?.code ?? worst.code;
  const top_gap_pillar_label_de =
    KANZLEI_PILLAR_LABEL_DE[top_gap_pillar_code] ?? top_gap_pillar_code;

  const pillar_traffic: Record<BoardReadinessPillarKey, BoardReadinessTraffic> = {
    eu_ai_act: t.eu.status,
    iso_42001: t.iso.status,
    nis2: t.nis2.status,
    dsgvo: t.dsgvo.status,
  };

  const hr = t.eu.hr_total > 0;
  const board_report_stale = hr && !t.eu.board_fresh;

  const h = historyByTenant.get(t.tenant_id);
  const last_mandant_readiness_export_at = h?.last_mandant_readiness_export_at ?? null;
  const last_datev_bundle_export_at = h?.last_datev_bundle_export_at ?? null;
  const last_any_export_at = maxIsoTimestamps(last_mandant_readiness_export_at, last_datev_bundle_export_at);
  const last_review_marked_at = h?.last_review_marked_at ?? null;
  const last_review_note_de = h?.last_review_note_de ?? null;

  const exportFieldMalformed =
    isNonEmptyUnparsableIso(last_mandant_readiness_export_at) ||
    isNonEmptyUnparsableIso(last_datev_bundle_export_at);
  const never_any_export = !last_any_export_at;
  const dAny = daysSinceValidIso(last_any_export_at, nowMs);
  const any_export_stale =
    never_any_export ||
    exportFieldMalformed ||
    (dAny !== null && dAny > KANZLEI_ANY_EXPORT_MAX_AGE_DAYS);

  const reviewMalformed = isNonEmptyUnparsableIso(last_review_marked_at);
  const dRev = daysSinceValidIso(last_review_marked_at, nowMs);
  const review_stale =
    !last_review_marked_at?.trim() ||
    reviewMalformed ||
    (dRev !== null && dRev > KANZLEI_REVIEW_STALE_DAYS);

  const baseline_gap = t.readiness_class === "early_pilot";

  const gaps_heavy_without_recent_export = computeGapsHeavyWithoutRecentExport(
    open_points_count,
    any_export_stale,
  );

  const attention_flags_de: string[] = [];
  if (never_any_export && !exportFieldMalformed) {
    attention_flags_de.push("Noch kein Kanzlei-Export erfasst (Readiness- oder DATEV-ZIP-Export)");
  } else if (exportFieldMalformed) {
    attention_flags_de.push("Export-Zeitstempel in der Historie ungültig (Readiness/DATEV prüfen)");
  } else if (any_export_stale) {
    attention_flags_de.push(
      `Letzter Export älter als ${KANZLEI_ANY_EXPORT_MAX_AGE_DAYS} Tage (jüngster Readiness/DATEV)`,
    );
  }
  if (review_stale) {
    attention_flags_de.push(
      `Review überfällig oder nicht erfasst (>${KANZLEI_REVIEW_STALE_DAYS} Tage)`,
    );
  }
  if (gaps_heavy_without_recent_export) {
    attention_flags_de.push(
      `Viele offene Prüfpunkte (≥${KANZLEI_GAP_HEAVY_FOR_EXPORT_RULE}) ohne frischen Export`,
    );
  }
  if (board_report_stale) attention_flags_de.push("Mandanten-/Board-Report überfällig");
  if (open_points_count >= KANZLEI_MANY_OPEN_POINTS) attention_flags_de.push("Viele offene Prüfpunkte");
  if (baseline_gap) attention_flags_de.push("Governance-Baseline noch dünn (Pilot)");
  if (!t.raw.fetch_ok) attention_flags_de.push("API teilweise nicht lesbar");

  const worstOverall = PILLAR_ORDER.reduce(
    (acc, k) => worstTraffic(acc, pillar_traffic[k]),
    "green" as BoardReadinessTraffic,
  );
  if (worstOverall === "red" && !attention_flags_de.some((x) => x.includes("überfällig"))) {
    attention_flags_de.push("Mindestens eine Säule rot");
  }

  const attention_score = kanzleiAttentionScore({
    open_points_count,
    open_points_hoch,
    board_report_stale,
    any_export_stale,
    baseline_gap,
    api_fetch_ok: t.raw.fetch_ok,
    pillar_traffic,
    review_stale,
    gaps_heavy_without_recent_export,
  });

  const tidEnc = encodeURIComponent(t.tenant_id);
  return {
    tenant_id: t.tenant_id,
    mandant_label: t.tenant_label,
    readiness_class: t.readiness_class,
    readiness_label_de: GTM_READINESS_LABELS_DE[t.readiness_class],
    primary_segment_label_de: segmentLabel(t.primary_segment),
    open_points_count,
    open_points_hoch,
    top_gap_pillar_code,
    top_gap_pillar_label_de,
    pillar_traffic,
    board_report_stale,
    api_fetch_ok: t.raw.fetch_ok,
    attention_score,
    attention_flags_de,
    last_mandant_readiness_export_at,
    last_datev_bundle_export_at,
    last_any_export_at,
    last_review_marked_at,
    last_review_note_de,
    review_stale,
    any_export_stale,
    never_any_export,
    gaps_heavy_without_recent_export,
    open_reminders_count: 0,
    next_reminder_due_at: null,
    links: {
      mandant_export_page: `/admin/advisor-mandant-export?client_id=${tidEnc}`,
      datev_bundle_api: `/api/internal/advisor/datev-export-bundle?client_id=${tidEnc}`,
      readiness_export_api: `/api/internal/advisor/mandant-readiness-export?client_id=${tidEnc}`,
      board_readiness_admin: "/admin/board-readiness",
    },
  };
}

function assemblePortfolioPayloadWithoutSla(
  bundle: {
    generated_at: string;
    backend_reachable: boolean;
    tenantIds: string[];
    tenants_partial: number;
  },
  rows: KanzleiPortfolioRow[],
  attention_queue: KanzleiAttentionQueueItem[],
  remState: AdvisorMandantRemindersState,
  nowMs: number,
): Omit<KanzleiPortfolioPayload, "advisor_sla"> {
  const openReminderRecords = remState.reminders.filter((r) => r.status === "open");
  const openByTenant = new Map<string, typeof openReminderRecords>();
  for (const r of openReminderRecords) {
    const arr = openByTenant.get(r.tenant_id) ?? [];
    arr.push(r);
    openByTenant.set(r.tenant_id, arr);
  }
  for (const arr of openByTenant.values()) {
    arr.sort((a, b) => Date.parse(a.due_at) - Date.parse(b.due_at));
  }

  const labelByTenant = new Map(rows.map((r) => [r.tenant_id, r.mandant_label]));
  const rowsWithReminders = rows.map((row) => {
    const list = openByTenant.get(row.tenant_id) ?? [];
    return {
      ...row,
      open_reminders_count: list.length,
      next_reminder_due_at: list[0]?.due_at ?? null,
    };
  });

  const open_reminders: MandantReminderApiEntry[] = [...openReminderRecords]
    .sort((a, b) => Date.parse(a.due_at) - Date.parse(b.due_at))
    .map((r) => ({
      reminder_id: r.reminder_id,
      tenant_id: r.tenant_id,
      mandant_label: labelByTenant.get(r.tenant_id) ?? null,
      category: r.category,
      due_at: r.due_at,
      note: r.note,
      source: r.source,
    }));

  let reminders_due_today_or_overdue_count = 0;
  let reminders_due_this_week_open_count = 0;
  for (const r of openReminderRecords) {
    if (isDueTodayOrOverdue(r.due_at, nowMs)) reminders_due_today_or_overdue_count += 1;
    if (isDueThisCalendarWeek(r.due_at, nowMs)) reminders_due_this_week_open_count += 1;
  }

  return {
    version: KANZLEI_PORTFOLIO_VERSION,
    generated_at: bundle.generated_at,
    backend_reachable: bundle.backend_reachable,
    mapped_tenant_count: bundle.tenantIds.length,
    tenants_partial: bundle.tenants_partial,
    constants: {
      review_stale_days: KANZLEI_REVIEW_STALE_DAYS,
      any_export_max_age_days: KANZLEI_ANY_EXPORT_MAX_AGE_DAYS,
      many_open_points_threshold: KANZLEI_MANY_OPEN_POINTS,
      gap_heavy_min_open_for_export_rule: KANZLEI_GAP_HEAVY_FOR_EXPORT_RULE,
    },
    rows: rowsWithReminders,
    attention_queue,
    open_reminders,
    reminders_due_today_or_overdue_count,
    reminders_due_this_week_open_count,
  };
}

export type ComputeKanzleiPortfolioOptions = {
  /** Vermeidet doppeltes Laden wenn Snapshots bereits für AI-Governance o. ä. geholt wurden. */
  preloadedBundle?: MappedTenantPillarSnapshotBundle;
};

export async function computeKanzleiPortfolioPayload(
  now: Date = new Date(),
  opts?: ComputeKanzleiPortfolioOptions,
): Promise<KanzleiPortfolioPayload> {
  const [bundle, historyByTenant] = await Promise.all([
    opts?.preloadedBundle ?? loadMappedTenantPillarSnapshots(now),
    readAdvisorMandantHistoryMap(),
  ]);
  const nowMs = bundle.nowMs;

  const rows = bundle.snapshots
    .map((s) => rowFromSnapshot(s, nowMs, historyByTenant))
    .sort((a, b) => {
      if (b.attention_score !== a.attention_score) return b.attention_score - a.attention_score;
      if (b.open_points_count !== a.open_points_count) return b.open_points_count - a.open_points_count;
      return (a.mandant_label ?? a.tenant_id).localeCompare(b.mandant_label ?? b.tenant_id, "de");
    });

  const attention_queue = buildAttentionQueue(rows, KANZLEI_MANY_OPEN_POINTS);

  let remState = await syncAdvisorMandantRemindersFromPortfolio(
    rows,
    KANZLEI_MANY_OPEN_POINTS,
    nowMs,
  );

  const bundleMeta = {
    generated_at: bundle.generated_at,
    backend_reachable: bundle.backend_reachable,
    tenantIds: bundle.tenantIds,
    tenants_partial: bundle.tenants_partial,
  };

  const basePayload = assemblePortfolioPayloadWithoutSla(bundleMeta, rows, attention_queue, remState, nowMs);
  const payloadForKpi: KanzleiPortfolioPayload = {
    ...basePayload,
    advisor_sla: stubAdvisorSlaEvaluation(new Date(nowMs).toISOString()),
  };
  const kpiSnapshot = await attachAdvisorKpiToPayload(payloadForKpi, nowMs, 90);

  const prevSla = await readAdvisorSlaSignalState();
  const slaEval = evaluateAdvisorSla({
    payload: payloadForKpi,
    kpiSnapshot,
    nowMs,
    previousCriticalRuleIds: prevSla.critical_rule_ids,
  });
  await writeAdvisorSlaSignalState(criticalRuleIdsFromFindings(slaEval.findings));

  const escalate =
    Boolean(slaEval.signals.find((s) => s.signal_id === "portfolio_red")?.active) ||
    Boolean(slaEval.signals.find((s) => s.signal_id === "partner_attention_required")?.active);
  await syncAdvisorSlaEscalationReminders(attention_queue, escalate, nowMs);

  remState = await readAdvisorMandantRemindersState();
  const finalBase = assemblePortfolioPayloadWithoutSla(bundleMeta, rows, attention_queue, remState, nowMs);
  return { ...finalBase, advisor_sla: slaEval };
}
