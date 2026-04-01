"use client";

/**
 * Leichtgewichtige Client-Events (Vercel/Server-Logs via `/api/marketing-event`).
 * Keine Drittanbieter-Analytics; keine sensiblen Formularinhalte.
 */

export type MarketingClientEvent =
  | "cta_click"
  | "lead_form_started"
  | "lead_form_submit_attempt"
  | "lead_form_submitted"
  | "lead_form_submit_error"
  | "lead_form_rate_limited";

export function sendMarketingEvent(payload: {
  event: MarketingClientEvent;
  cta_id?: string;
  quelle?: string;
  /** Nur bei Submit: forwarded | stored | stored_forward_failed */
  delivery?: string;
}): void {
  if (typeof navigator === "undefined") return;
  try {
    const body = JSON.stringify({
      ...payload,
      t: Date.now(),
    });
    const blob = new Blob([body], { type: "application/json" });
    const ok = navigator.sendBeacon("/api/marketing-event", blob);
    if (!ok) {
      void fetch("/api/marketing-event", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
        keepalive: true,
      });
    }
  } catch {
    /* ignore */
  }
}
