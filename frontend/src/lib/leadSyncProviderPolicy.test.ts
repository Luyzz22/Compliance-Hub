import { afterEach, describe, expect, it, vi } from "vitest";

import { getEnabledLeadSyncTargets } from "@/lib/leadSyncDispatcher";
import { runLeadSyncConnector } from "@/lib/leadSyncConnectors";
import type { LeadSyncPayloadV1 } from "@/lib/leadSyncTypes";

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("lead sync production provider policy", () => {
  it("fails closed when a forbidden CRM token is configured", () => {
    vi.stubEnv("COMPLIANCEHUB_RELEASE_CHANNEL", "production");
    vi.stubEnv("HUBSPOT_ACCESS_TOKEN", "forbidden-token");
    expect(() => getEnabledLeadSyncTargets()).toThrow("US CRM connectors are forbidden");
  });

  it("rejects direct connector execution in production", async () => {
    vi.stubEnv("COMPLIANCEHUB_RELEASE_CHANNEL", "production");
    const payload = {} as LeadSyncPayloadV1;

    await expect(runLeadSyncConnector("hubspot", payload)).resolves.toMatchObject({
      ok: false,
      retryable: false,
    });
    await expect(runLeadSyncConnector("pipedrive", payload)).resolves.toMatchObject({
      ok: false,
      retryable: false,
    });
  });

  it("requires a mounted bearer secret for production webhooks", async () => {
    vi.stubEnv("COMPLIANCEHUB_RELEASE_CHANNEL", "production");
    vi.stubEnv("COMPLIANCEHUB_OUTBOUND_WEBHOOK_ALLOWED_HOSTS", "n8n.internal.example");
    vi.stubEnv("LEAD_SYNC_N8N_URL", "https://n8n.internal.example/hooks/leads");

    await expect(
      runLeadSyncConnector("n8n_webhook", {} as LeadSyncPayloadV1),
    ).rejects.toThrow("LEAD_SYNC_N8N_SECRET_FILE is required");
  });
});
