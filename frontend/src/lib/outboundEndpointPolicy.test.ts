import { afterEach, describe, expect, it, vi } from "vitest";

import {
  approvedPrivateServiceBaseUrl,
  approvedOutboundWebhookUrl,
  approvedVersionedApiPath,
  crmProviderIsForbiddenInProduction,
} from "@/lib/outboundEndpointPolicy";

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("sovereign outbound endpoint policy", () => {
  it("allows only explicit private-service hosts in production", () => {
    vi.stubEnv("COMPLIANCEHUB_RELEASE_CHANNEL", "production");
    vi.stubEnv("COMPLIANCEHUB_API_ALLOWED_HOSTS", "backend");

    expect(
      approvedPrivateServiceBaseUrl(
        "http://backend:8000",
        "COMPLIANCEHUB_API_BASE_URL",
        "COMPLIANCEHUB_API_ALLOWED_HOSTS",
      ),
    ).toBe("http://backend:8000");
    expect(() =>
      approvedPrivateServiceBaseUrl(
        "https://attacker.example",
        "COMPLIANCEHUB_API_BASE_URL",
        "COMPLIANCEHUB_API_ALLOWED_HOSTS",
      ),
    ).toThrow("must be listed");
    expect(() =>
      approvedPrivateServiceBaseUrl(
        "http://backend:8000/path?token=secret",
        "COMPLIANCEHUB_API_BASE_URL",
        "COMPLIANCEHUB_API_ALLOWED_HOSTS",
      ),
    ).toThrow("bare HTTP");
  });

  it("accepts an explicitly allowlisted self-hosted HTTPS endpoint", () => {
    vi.stubEnv("COMPLIANCEHUB_RELEASE_CHANNEL", "production");
    vi.stubEnv("COMPLIANCEHUB_OUTBOUND_WEBHOOK_ALLOWED_HOSTS", "n8n.internal.example");

    expect(
      approvedOutboundWebhookUrl(
        "https://n8n.internal.example/hooks/compliancehub",
        "LEAD_SYNC_N8N_URL",
      ),
    ).toBe("https://n8n.internal.example/hooks/compliancehub");
  });

  it("rejects forbidden providers even when an operator allowlists the host", () => {
    vi.stubEnv("COMPLIANCEHUB_RELEASE_CHANNEL", "production");
    vi.stubEnv("COMPLIANCEHUB_OUTBOUND_WEBHOOK_ALLOWED_HOSTS", "api.hubapi.com");

    expect(() =>
      approvedOutboundWebhookUrl("https://api.hubapi.com/webhook", "WEBHOOK_URL"),
    ).toThrow("provider forbidden");
  });

  it("rejects plaintext, query-secret and non-allowlisted production endpoints", () => {
    vi.stubEnv("COMPLIANCEHUB_RELEASE_CHANNEL", "production");
    vi.stubEnv("COMPLIANCEHUB_OUTBOUND_WEBHOOK_ALLOWED_HOSTS", "n8n.internal.example");

    expect(() =>
      approvedOutboundWebhookUrl("http://n8n.internal.example/hook", "WEBHOOK_URL"),
    ).toThrow("HTTPS");
    expect(() =>
      approvedOutboundWebhookUrl(
        "https://n8n.internal.example/hook?token=secret",
        "WEBHOOK_URL",
      ),
    ).toThrow("query parameters");
    expect(() =>
      approvedOutboundWebhookUrl("https://other.example/hook", "WEBHOOK_URL"),
    ).toThrow("must be listed");
  });

  it("forbids both CRM providers in enterprise production", () => {
    vi.stubEnv("COMPLIANCEHUB_RELEASE_CHANNEL", "production");
    expect(crmProviderIsForbiddenInProduction("hubspot")).toBe(true);
    expect(crmProviderIsForbiddenInProduction("pipedrive")).toBe(true);
  });
});

describe("versioned backend API path policy", () => {
  it("preserves normalized versioned paths and query parameters", () => {
    expect(approvedVersionedApiPath("/api/v1/ai-systems?limit=20")).toBe(
      "/api/v1/ai-systems?limit=20",
    );
  });

  it.each([
    "/api/v1/../internal/health",
    "/api/v1/%2e%2e/internal/health",
    "/api/v1\\..\\internal\\health",
    "https://attacker.invalid/api/v1/data",
    "/api/v1/data#credential",
  ])("rejects an unsafe backend path: %s", (path) => {
    expect(() => approvedVersionedApiPath(path)).toThrow("normalized versioned");
  });
});
