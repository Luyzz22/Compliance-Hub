/**
 * Einfaches IP-Rate-Limit (pro Node-Prozess).
 * In verteilten Umgebungen ggf. durch Redis/Edge-Rate-Limit ersetzen.
 */

const WINDOW_MS = 15 * 60 * 1000;
const MAX_PER_WINDOW = 12;

type Bucket = { resetAt: number; count: number };

const ipBuckets = new Map<string, Bucket>();

export function checkLeadIpRateLimit(clientIp: string): { ok: true } | { ok: false; retry_after_sec: number } {
  const ip = clientIp.trim() || "unknown";
  const now = Date.now();
  let b = ipBuckets.get(ip);
  if (!b || now >= b.resetAt) {
    b = { resetAt: now + WINDOW_MS, count: 0 };
    ipBuckets.set(ip, b);
  }
  if (b.count >= MAX_PER_WINDOW) {
    return { ok: false, retry_after_sec: Math.ceil((b.resetAt - now) / 1000) };
  }
  b.count += 1;
  pruneBuckets(now);
  return { ok: true };
}

function pruneBuckets(now: number) {
  if (ipBuckets.size < 2000) return;
  for (const [k, v] of ipBuckets) {
    if (now >= v.resetAt) ipBuckets.delete(k);
  }
}

export function getClientIp(req: Request): string {
  const xf = req.headers.get("x-forwarded-for");
  if (xf) {
    const first = xf.split(",")[0]?.trim();
    if (first) return first.slice(0, 64);
  }
  const real = req.headers.get("x-real-ip");
  if (real) return real.trim().slice(0, 64);
  return "unknown";
}
