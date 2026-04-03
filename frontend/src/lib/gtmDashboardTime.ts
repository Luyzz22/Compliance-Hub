/** Reine Zeitfenster-Hilfen (ohne server-only) für Tests + Aggregation. */

const MS_PER_DAY = 86_400_000;

export type GtmWindowKey = "7d" | "30d";

export function windowBoundsMs(days: number, nowMs: number): { start: number; end: number } {
  return { start: nowMs - days * MS_PER_DAY, end: nowMs };
}

export function isoInWindow(iso: string, startMs: number, endMs: number): boolean {
  const t = Date.parse(iso);
  if (!Number.isFinite(t)) return false;
  return t >= startMs && t <= endMs;
}

export function utcDayKeyFromMs(ms: number): string {
  return new Date(ms).toISOString().slice(0, 10);
}

/** Montag 00:00 UTC der Kalenderwoche. */
export function utcWeekStartMondayFromMs(ms: number): string {
  const d = new Date(ms);
  const day = d.getUTCDay();
  const mondayOffset = (day + 6) % 7;
  d.setUTCDate(d.getUTCDate() - mondayOffset);
  d.setUTCHours(0, 0, 0, 0);
  return d.toISOString().slice(0, 10);
}

export { MS_PER_DAY };
