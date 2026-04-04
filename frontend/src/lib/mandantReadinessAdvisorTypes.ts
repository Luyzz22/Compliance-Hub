/**
 * Wave 37 – Mandanten-Readiness-Export für Steuerberater / WP / Advisor (intern).
 */

export const MANDANT_READINESS_EXPORT_VERSION = "wave37-v1";

/** Abschnitt 1 – Mandantenstatus kompakt */
export type MandantReadinessKompakt = {
  mandant_id: string;
  mandanten_bezeichnung: string;
  /** Kurztext, keine Board-Ampel-Sprache */
  readiness_kurzfassung_de: string;
  ki_systeme_gesamt: number;
  ki_hochrisiko_anzahl: number;
  /** Aus Wave-33-ähnlicher Klassifikation (Pilot/Baseline/…) */
  governance_reifeklasse_de: string;
  /** Freitext aus Setup-Rollen, falls vorhanden */
  ansprechpartner_hinweis_de: string;
  hauptbedenken_de: string[];
};

/** Abschnitt 2 – Offene Punkte (Prüfpunkte) */
export type MandantReadinessOffenerPunktExport = {
  prioritaet: "hoch" | "mittel";
  pruefpunkt_de: string;
  referenz_id: string;
  ki_system?: string;
  letzte_aenderung_iso?: string | null;
};

/** Abschnitt 3 – Nächste Schritte */
export type MandantReadinessNaechsterSchritt = {
  schritt_de: string;
  fuer: "mandant" | "kanzlei" | "gemeinsam";
};

/** Abschnitt 4 – Nachweise / Export */
export type MandantReadinessNachweisHinweis = {
  label_de: string;
  wert_de: string;
};

export type MandantReadinessAdvisorMeta = {
  generated_at: string;
  quelle_dashboard_stand: string;
  api_erreichbar: boolean;
  hinweis_de: string;
};

export type MandantReadinessAdvisorPayload = {
  version: typeof MANDANT_READINESS_EXPORT_VERSION;
  kompakt: MandantReadinessKompakt;
  offene_punkte: MandantReadinessOffenerPunktExport[];
  naechste_schritte: MandantReadinessNaechsterSchritt[];
  nachweise: MandantReadinessNachweisHinweis[];
  markdown_de: string;
  meta: MandantReadinessAdvisorMeta;
};
