const CONSUMER_DOMAINS = new Set([
  "gmail.com",
  "googlemail.com",
  "yahoo.com",
  "yahoo.de",
  "hotmail.com",
  "outlook.com",
  "live.com",
  "icloud.com",
  "gmx.de",
  "gmx.net",
  "web.de",
  "t-online.de",
]);

/**
 * Optional: Nur geschäftliche Domains (Env `LEAD_REQUIRE_BUSINESS_EMAIL=1`).
 */
export function validateBusinessEmailDomain(
  email: string,
  requireBusiness: boolean,
): { ok: true } | { ok: false } {
  if (!requireBusiness) return { ok: true };
  const at = email.lastIndexOf("@");
  if (at < 0) return { ok: false };
  const domain = email.slice(at + 1).toLowerCase();
  if (CONSUMER_DOMAINS.has(domain)) return { ok: false };
  return { ok: true };
}

const MIN_FORM_MS = 2500;
const MAX_FORM_MS = 3 * 60 * 60 * 1000;

/** Client-setzter Timestamp (ms) beim Öffnen des Formulars. */
export function validateFormTiming(formOpenedAt: number | undefined): { ok: true } | { ok: false } {
  if (formOpenedAt === undefined || !Number.isFinite(formOpenedAt)) {
    return { ok: false };
  }
  const elapsed = Date.now() - formOpenedAt;
  if (elapsed < MIN_FORM_MS || elapsed > MAX_FORM_MS) {
    return { ok: false };
  }
  return { ok: true };
}
