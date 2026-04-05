/** Gemeinsame ISO-Zeitvergleiche für Mandanten-Historie (ohne server-only). */

export function isParseableIso(s: string | null | undefined): boolean {
  const t = s?.trim();
  if (!t) return false;
  return !Number.isNaN(Date.parse(t));
}

/** Nicht-leer, aber kein gültiger Zeitstempel (Legacy/manuelle JSON-Fehler). */
export function isNonEmptyUnparsableIso(s: string | null | undefined): boolean {
  const t = s?.trim();
  if (!t) return false;
  return Number.isNaN(Date.parse(t));
}

export function maxIsoTimestamps(a: string | null | undefined, b: string | null | undefined): string | null {
  const x = a?.trim() || null;
  const y = b?.trim() || null;
  if (!x && !y) return null;
  if (!x) return y !== null && isParseableIso(y) ? y : null;
  if (!y) return x !== null && isParseableIso(x) ? x : null;
  const tx = Date.parse(x);
  const ty = Date.parse(y);
  const vx = Number.isNaN(tx) ? null : tx;
  const vy = Number.isNaN(ty) ? null : ty;
  if (vx === null && vy === null) return null;
  if (vx === null) return y;
  if (vy === null) return x;
  return vx >= vy ? x : y;
}

export function daysSinceValidIso(iso: string | null | undefined, nowMs: number): number | null {
  if (!iso?.trim()) return null;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return null;
  return Math.floor((nowMs - t) / (24 * 60 * 60 * 1000));
}
