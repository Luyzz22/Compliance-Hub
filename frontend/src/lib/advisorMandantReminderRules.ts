/**
 * Wave 43 – Regeln für automatische Reminder (ohne server-only, testbar).
 */

import { rowQualifiesForAttentionQueue } from "@/lib/kanzleiAttentionQueue";
import type { KanzleiPortfolioRow } from "@/lib/kanzleiPortfolioTypes";
import type { MandantReminderCategory } from "@/lib/advisorMandantReminderTypes";

/** Kategorien, die beim Portfolio-Sync gesetzt/aktualisiert werden. */
export const AUTO_MANDANT_REMINDER_CATEGORIES: MandantReminderCategory[] = [
  "stale_review",
  "stale_export",
  "high_gap_count",
  "portfolio_attention",
];

/** Fälligkeit für Auto-Reminder: Ende der lokalen Kalenderwoche (Sonntag 23:59:59). */
export function defaultAutoDueAtIso(nowMs: number): string {
  const d = new Date(nowMs);
  const dow = d.getDay();
  const daysToSunday = dow === 0 ? 0 : 7 - dow;
  d.setDate(d.getDate() + daysToSunday);
  d.setHours(23, 59, 59, 999);
  return d.toISOString();
}

export function autoReminderStaleReviewActive(row: KanzleiPortfolioRow): boolean {
  return row.review_stale;
}

export function autoReminderStaleExportActive(row: KanzleiPortfolioRow): boolean {
  return row.any_export_stale || row.never_any_export;
}

export function autoReminderHighGapActive(row: KanzleiPortfolioRow, manyOpenThreshold: number): boolean {
  return row.open_points_count >= manyOpenThreshold || row.open_points_hoch >= 2;
}

export function autoReminderPortfolioAttentionActive(
  row: KanzleiPortfolioRow,
  manyOpenThreshold: number,
): boolean {
  return rowQualifiesForAttentionQueue(row, manyOpenThreshold);
}

export function isAutoReminderConditionActive(
  row: KanzleiPortfolioRow,
  category: MandantReminderCategory,
  manyOpenThreshold: number,
): boolean {
  switch (category) {
    case "stale_review":
      return autoReminderStaleReviewActive(row);
    case "stale_export":
      return autoReminderStaleExportActive(row);
    case "high_gap_count":
      return autoReminderHighGapActive(row, manyOpenThreshold);
    case "portfolio_attention":
      return autoReminderPortfolioAttentionActive(row, manyOpenThreshold);
    default:
      return false;
  }
}

/** Montag 00:00:00 lokal bis Sonntag 23:59:59 – grobe „diese Woche“-Grenze. */
export function isDueThisCalendarWeek(dueAtIso: string, nowMs: number): boolean {
  const due = Date.parse(dueAtIso);
  if (Number.isNaN(due)) return false;
  const now = new Date(nowMs);
  const start = new Date(now);
  const day = start.getDay();
  const daysFromMonday = day === 0 ? 6 : day - 1;
  start.setDate(start.getDate() - daysFromMonday);
  start.setHours(0, 0, 0, 0);
  const end = new Date(start);
  end.setDate(end.getDate() + 7);
  end.setMilliseconds(-1);
  return due >= start.getTime() && due <= end.getTime();
}

export function isDueTodayOrOverdue(dueAtIso: string, nowMs: number): boolean {
  const due = Date.parse(dueAtIso);
  if (Number.isNaN(due)) return false;
  const endOfToday = new Date(nowMs);
  endOfToday.setHours(23, 59, 59, 999);
  return due <= endOfToday.getTime();
}
