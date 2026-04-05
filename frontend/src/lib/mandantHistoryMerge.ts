/** Gemeinsame ISO-Zeitvergleiche für Mandanten-Historie (ohne server-only). */

export function maxIsoTimestamps(a: string | null | undefined, b: string | null | undefined): string | null {
  const x = a?.trim() || null;
  const y = b?.trim() || null;
  if (!x) return y;
  if (!y) return x;
  return Date.parse(x) >= Date.parse(y) ? x : y;
}
