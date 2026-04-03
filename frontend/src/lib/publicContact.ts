/**
 * Öffentlicher Kontakt (kanonische Homepage: complywithai.de).
 * Primär: Formular unter `PUBLIC_CONTACT_PATH` (Wave 24).
 * Fallback: direktes `mailto:` bei technischen Störungen.
 */
export const PUBLIC_CONTACT_EMAIL = "kontakt@complywithai.de";
export const PUBLIC_CONTACT_MAILTO = `mailto:${PUBLIC_CONTACT_EMAIL}`;
export const PUBLIC_CONTACT_PATH = "/kontakt" as const;

export type ContactPageHrefOpts = {
  quelle: string;
  /** Technischer CTA-Code (z. B. home-hero-demo) */
  ctaId?: string;
  /** Kurzes Anzeige-Label (z. B. Demo, Kontakt) */
  ctaLabel?: string;
};

/** `quelle` = Query-Parameter für Sales-Triage (z. B. home-hero, footer). */
export function contactPageHref(quelle: string): string;
export function contactPageHref(opts: ContactPageHrefOpts): string;
export function contactPageHref(quelleOrOpts: string | ContactPageHrefOpts): string {
  const opts: ContactPageHrefOpts =
    typeof quelleOrOpts === "string"
      ? { quelle: quelleOrOpts }
      : { ...quelleOrOpts, quelle: quelleOrOpts.quelle };
  const q = (opts.quelle.trim() || "unbekannt").slice(0, 120);
  const p = new URLSearchParams();
  p.set("quelle", q);
  if (opts.ctaId?.trim()) p.set("cta_id", opts.ctaId.trim().slice(0, 80));
  if (opts.ctaLabel?.trim()) p.set("cta_label", opts.ctaLabel.trim().slice(0, 120));
  return `${PUBLIC_CONTACT_PATH}?${p.toString()}`;
}
