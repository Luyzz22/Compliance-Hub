/**
 * Wave 31 – Schwellen für GTM Health (regelbasiert, bewusst grob).
 * Anpassungen hier statt in UI-Komponenten.
 */

/** Webhook-Fehlerquote (fehlgeschlagen / Inbound 30d) */
export const GTM_HEALTH_WEBHOOK_RATE_WATCH = 0.05;
export const GTM_HEALTH_WEBHOOK_RATE_ISSUE = 0.12;

/** Spam-Anteil (Triage spam / Inbound 30d), nur ab Mindestvolumen */
export const GTM_HEALTH_SPAM_RATE_MIN_INBOUND = 5;
export const GTM_HEALTH_SPAM_RATE_WATCH = 0.08;
export const GTM_HEALTH_SPAM_RATE_ISSUE = 0.18;

/** „Neu“-Leads älter als X Tage (Triage received) */
export const GTM_HEALTH_UNTRIAGED_DAYS = 3;
export const GTM_HEALTH_UNTRIAGED_COUNT_WATCH = 2;
export const GTM_HEALTH_UNTRIAGED_COUNT_ISSUE = 5;

/** CRM: fehlgeschlagene + Dead-Letter-Jobs 30d vs. erfolgreiche Sends */
export const GTM_HEALTH_CRM_BAD_RATIO_MIN_DENOM = 4;
export const GTM_HEALTH_CRM_BAD_RATIO_WATCH = 0.25;
export const GTM_HEALTH_CRM_BAD_RATIO_ISSUE = 0.45;

/** Pipeline: Deals / qualifiziert (30d) */
export const GTM_HEALTH_PIPELINE_QUALIFIED_MIN = 3;
export const GTM_HEALTH_DEAL_TO_QUALIFIED_WATCH = 0.15;
export const GTM_HEALTH_DEAL_TO_QUALIFIED_ISSUE = 0.05;

/** Sync: letzter Versuch älter als X h, Status failed (CRM) */
export const GTM_HEALTH_STUCK_SYNC_HOURS = 24;

/** Qualifiziert ohne Pipedrive-Deal, Proxy: Einreichung > X Tage */
export const GTM_HEALTH_QUALIFIED_NO_DEAL_DAYS = 7;

/** Segment: „viel rein, wenig qualifiziert“ */
export const GTM_HEALTH_SEGMENT_VOLUME_MIN = 6;
export const GTM_HEALTH_SEGMENT_QUAL_RATIO_LOW = 0.12;

/** Segment: GTM-Fokus-Lücke */
export const GTM_HEALTH_SEGMENT_VOLUME_VERY_LOW = 2;

/** Attribution: Noise-Verdacht */
export const GTM_HEALTH_ATTRIB_NOISE_MIN_LEADS = 4;
export const GTM_HEALTH_ATTRIB_NOISE_MAX_QUAL_RATIO = 0.12;
