import type { GtmAlertFinding } from "@/lib/gtmAlertEvaluator";

export type GtmAlertDispatchPayload = {
  generated_at: string;
  findings: GtmAlertFinding[];
  summary_de: string;
  health_snapshot_url_hint: string;
};

/**
 * Minimal Ausleitung: strukturiertes Log + optional generischer Webhook (n8n, Slack Incoming, …).
 */
export async function dispatchGtmAlertFindings(payload: GtmAlertDispatchPayload): Promise<void> {
  console.info("[gtm-alert-wave32]", JSON.stringify(payload));

  const url = process.env.GTM_ALERT_WEBHOOK_URL?.trim();
  if (!url) return;

  try {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source: "compliancehub-gtm",
        ...payload,
      }),
    });
    if (!r.ok) {
      console.warn("[gtm-alert-wave32] webhook_http", r.status, await r.text().catch(() => ""));
    }
  } catch (e) {
    console.warn("[gtm-alert-wave32] webhook_error", e);
  }
}
