/**
 * Verhindert Burst-Duplikate derselben geschäftlichen E-Mail (pro Prozess).
 */

const COOLDOWN_MS = 5 * 60 * 1000;
const emailLastSeen = new Map<string, number>();

export function checkLeadEmailCooldown(
  normalizedEmail: string,
): { ok: true } | { ok: false; retry_after_sec: number } {
  const email = normalizedEmail.toLowerCase().trim();
  const now = Date.now();
  const last = emailLastSeen.get(email);
  if (last !== undefined && now - last < COOLDOWN_MS) {
    return {
      ok: false,
      retry_after_sec: Math.ceil((COOLDOWN_MS - (now - last)) / 1000),
    };
  }
  emailLastSeen.set(email, now);
  if (emailLastSeen.size > 5000) {
    for (const [k, t] of emailLastSeen) {
      if (now - t > COOLDOWN_MS * 4) emailLastSeen.delete(k);
    }
  }
  return { ok: true };
}

export function rollbackLeadEmailCooldown(normalizedEmail: string): void {
  emailLastSeen.delete(normalizedEmail.toLowerCase().trim());
}
