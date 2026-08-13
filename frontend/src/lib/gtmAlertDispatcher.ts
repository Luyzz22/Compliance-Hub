import "server-only";

import type { GtmAlertFinding } from "@/lib/gtmAlertEvaluator";
import {
  approvedOutboundWebhookUrl,
  isEnterpriseProductionRuntime,
} from "@/lib/outboundEndpointPolicy";
import { readServerSecret } from "@/lib/serverSecret";

export type GtmAlertDispatchPayload = {
  generated_at: string;
  findings: GtmAlertFinding[];
  summary_de: string;
  health_snapshot_url_hint: string;
};

/**
 * Minimal Ausleitung: strukturiertes Log + optionaler, allowlist-geprüfter interner Webhook.
 */
export async function dispatchGtmAlertFindings(payload: GtmAlertDispatchPayload): Promise<void> {
  console.info("[gtm-alert-wave32]", {
    generated_at: payload.generated_at,
    finding_count: payload.findings.length,
    critical_count: payload.findings.filter((finding) => finding.severity === "critical").length,
  });

  const configuredUrl = process.env.GTM_ALERT_WEBHOOK_URL?.trim();
  if (!configuredUrl) return;

  try {
    const url = approvedOutboundWebhookUrl(configuredUrl, "GTM_ALERT_WEBHOOK_URL");
    const secret = readServerSecret({
      environmentVariable: "GTM_ALERT_WEBHOOK_SECRET",
      fileEnvironmentVariable: "GTM_ALERT_WEBHOOK_SECRET_FILE",
      minimumBytes: 32,
      required: isEnterpriseProductionRuntime(),
    });
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 20_000);
    try {
      const r = await fetch(url, {
        method: "POST",
        redirect: "manual",
        headers: {
          "Content-Type": "application/json",
          ...(secret ? { Authorization: `Bearer ${secret}` } : {}),
        },
        body: JSON.stringify({
          source: "compliancehub-gtm",
          ...payload,
        }),
        signal: controller.signal,
      });
      if (!r.ok) {
        console.warn("[gtm-alert-wave32] webhook_http", r.status);
      }
    } finally {
      clearTimeout(timer);
    }
  } catch (e) {
    console.warn("[gtm-alert-wave32] webhook_error", e);
  }
}
