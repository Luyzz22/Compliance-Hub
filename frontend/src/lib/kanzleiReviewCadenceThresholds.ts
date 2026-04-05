/**
 * Wave 40 – konservative Schwellen für Kanzlei-Review-Kadenz und Export-Historie.
 * Zentrale Konstanten für Portfolio-Scoring und UI-Hinweise.
 */

/** Review als „überfällig“, wenn älter als diese Tage oder nie gesetzt. */
export const KANZLEI_REVIEW_STALE_DAYS = 90;

/** Jüngster Export (Readiness-JSON oder DATEV-ZIP) darf nicht älter sein als X Tage. */
export const KANZLEI_ANY_EXPORT_MAX_AGE_DAYS = 90;

/** Ab dieser Anzahl offener Prüfpunkte gilt der Mandant als „lückenlastig“. */
export const KANZLEI_MANY_OPEN_POINTS = 4;

/** „Viele Lücken + kein frischer Export“: mindestens so viele offene Punkte. */
export const KANZLEI_GAP_HEAVY_FOR_EXPORT_RULE = 5;
