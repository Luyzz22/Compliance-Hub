/**
 * Wave 32 – Schwellen für automatisierte GTM-Alerts (Cron/n8n).
 * Unabhängig von Health-Kacheln; bewusst konservativ.
 */

/** „Neu“ >3 Tage – kritischer Rückstand */
export const GTM_ALERT_UNTRIAGED_CRITICAL = 8;
export const GTM_ALERT_UNTRIAGED_WARNING = 5;

/** CRM Dead Letters im 30-Tage-Fenster (alle Ziele im Snapshot-Zähler = Produktiv-CRM) */
export const GTM_ALERT_DEAD_LETTER_CRITICAL = 4;
export const GTM_ALERT_DEAD_LETTER_WARNING = 2;

/** Qualifiziert ohne Pipedrive-Deal, Proxy >7d Einreichung */
export const GTM_ALERT_QUAL_NO_DEAL_CRITICAL = 8;
export const GTM_ALERT_QUAL_NO_DEAL_WARNING = 5;
