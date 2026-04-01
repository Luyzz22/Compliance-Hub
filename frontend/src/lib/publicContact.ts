/**
 * Öffentlicher Kontakt (kanonische Homepage: complywithai.de).
 * Primär: Formular unter `PUBLIC_CONTACT_PATH` (Wave 24).
 * Fallback: direktes `mailto:` bei technischen Störungen.
 */
export const PUBLIC_CONTACT_EMAIL = "kontakt@complywithai.de";
export const PUBLIC_CONTACT_MAILTO = `mailto:${PUBLIC_CONTACT_EMAIL}`;
export const PUBLIC_CONTACT_PATH = "/kontakt" as const;

/** `quelle` = Query-Parameter für Sales-Triage (z. B. home-hero, footer). */
export function contactPageHref(quelle: string): string {
  const q = quelle.trim() || "unbekannt";
  return `${PUBLIC_CONTACT_PATH}?quelle=${encodeURIComponent(q)}`;
}
