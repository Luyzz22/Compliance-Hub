import { describe, expect, it } from "vitest";

import { attributionFromOutbound, buildLeadAttribution, emptyLeadAttribution } from "@/lib/leadAttribution";

describe("buildLeadAttribution", () => {
  it("classifies paid search from UTM", () => {
    const a = buildLeadAttribution({
      utm_source: "google",
      utm_medium: "cpc",
      utm_campaign: "ai-act-q2-2026",
      http_referer: null,
    });
    expect(a.source).toBe("paid_search");
    expect(a.medium).toBe("cpc");
    expect(a.campaign).toBe("ai-act-q2-2026");
  });

  it("uses LinkedIn source token", () => {
    const a = buildLeadAttribution({
      utm_source: "linkedin",
      utm_medium: "social",
      http_referer: null,
    });
    expect(a.source).toBe("linkedin");
  });

  it("treats empty UTM and referrers as direct", () => {
    const a = buildLeadAttribution({
      http_referer: null,
      page_referrer: "",
    });
    expect(a.source).toBe("direct");
  });

  it("infers organic search from Google referer host", () => {
    const a = buildLeadAttribution({
      http_referer: "https://www.google.com/search?q=compliance",
    });
    expect(a.source).toBe("organic_search");
    expect(a.referrer_host).toBe("www.google.com");
  });

  it("stores CTA fields", () => {
    const a = buildLeadAttribution({
      cta_id: "home-hero-demo",
      cta_label: "Demo anfragen",
      http_referer: null,
    });
    expect(a.cta_id).toBe("home-hero-demo");
    expect(a.cta_label).toBe("Demo anfragen");
  });
});

describe("attributionFromOutbound", () => {
  it("returns unknown when outbound has no attribution", () => {
    expect(attributionFromOutbound({})).toEqual(emptyLeadAttribution());
  });
});
