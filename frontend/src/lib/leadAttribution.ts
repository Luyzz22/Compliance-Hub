/**
 * Wave 30 – leichte Attribution (UTM, Referrer, CTA) ohne Multi-Touch-Engine.
 * Ableitung ist heuristisch; Werte sind interne Steuerungsgrößen, keine „Wahrheit“.
 */

export const LEAD_ATTRIBUTION_SOURCES = [
  "direct",
  "organic_search",
  "referral",
  "linkedin",
  "newsletter",
  "paid_search",
  "paid_social",
  "email",
  "other",
  "unknown",
] as const;

export type LeadAttributionSource = (typeof LEAD_ATTRIBUTION_SOURCES)[number];

/** Gespeichert in Outbound (schema ≥ 1.2) und gespiegelt in Inbox. */
export type LeadAttributionSnapshot = {
  source: LeadAttributionSource;
  /** Normalisiertes Medium (z. B. cpc, email, paid_social) oder leer */
  medium: string;
  /** Kurzcode aus utm_campaign, Kleinbuchstaben/Zahlen/_/- */
  campaign: string;
  /** Technischer CTA-Bezeichner (Link/Event) */
  cta_id: string;
  /** Anzeige-Label für Menschen (z. B. „Demo“) */
  cta_label: string;
  utm_source_raw: string;
  utm_medium_raw: string;
  utm_campaign_raw: string;
  /** Host der HTTP-Referer-URL (serverseitig), nicht die volle URL */
  referrer_host: string;
};

export const LEAD_ATTRIBUTION_LIMITS = {
  utm: 120,
  medium: 64,
  campaign: 120,
  cta_id: 80,
  cta_label: 120,
  referrer: 500,
  referrer_host: 253,
} as const;

function slugMedium(s: string): string {
  const t = s.trim().toLowerCase().slice(0, LEAD_ATTRIBUTION_LIMITS.medium);
  return t.replace(/[^a-z0-9_+-]+/g, "_").replace(/_+/g, "_").replace(/^_|_$/g, "");
}

function slugCampaign(s: string): string {
  const t = s.trim().toLowerCase().slice(0, LEAD_ATTRIBUTION_LIMITS.campaign);
  return t.replace(/[^a-z0-9_+-]+/g, "-").replace(/-+/g, "-").replace(/^-|-$/g, "");
}

function trimField(s: unknown, max: number): string {
  if (typeof s !== "string") return "";
  return s.trim().slice(0, max);
}

function parseUrlHost(raw: string): string {
  const t = raw.trim().slice(0, LEAD_ATTRIBUTION_LIMITS.referrer);
  if (!t) return "";
  try {
    const u = new URL(t);
    return u.hostname.toLowerCase().slice(0, LEAD_ATTRIBUTION_LIMITS.referrer_host);
  } catch {
    return "";
  }
}

function hostFromReferrerHeader(header: string | null): string {
  if (!header) return "";
  return parseUrlHost(header);
}

function hostFromPageReferrer(clientRef: string): string {
  return parseUrlHost(clientRef);
}

const SEARCH_HOST_FRAGMENTS = [
  "google.",
  "bing.",
  "duckduckgo.",
  "ecosia.",
  "startpage.",
  "yahoo.",
  "qwant.",
];

function isSearchHost(host: string): boolean {
  if (!host) return false;
  return SEARCH_HOST_FRAGMENTS.some((f) => host.includes(f));
}

function normalizeSourceToken(s: string): string {
  return s.trim().toLowerCase();
}

function deriveSourceFromUtm(
  utmSource: string,
  utmMedium: string,
): LeadAttributionSource | null {
  const src = normalizeSourceToken(utmSource);
  const med = normalizeSourceToken(utmMedium);
  if (!src && !med) return null;

  if (med === "cpc" || med === "ppc" || med === "paidsearch" || med === "paid_search") {
    return "paid_search";
  }
  if (med === "paid_social" || med === "paidsocial" || med === "social_paid") {
    return "paid_social";
  }
  if (med === "email" || med === "e-mail") {
    return "email";
  }
  if (med === "newsletter" || src.includes("newsletter") || src.includes("mailchimp")) {
    return "newsletter";
  }
  if (src.includes("linkedin") || src === "lnkd.in") {
    return "linkedin";
  }
  if (src === "google" && (med === "organic" || med === "referral" || !med)) {
    return "organic_search";
  }
  if (
    (src === "google" || src === "bing") &&
    (med === "organic" || med === "referral" || !med)
  ) {
    return "organic_search";
  }
  if (src && (med === "organic" || med === "natural")) {
    return "organic_search";
  }
  return null;
}

function deriveSourceFromHosts(
  httpReferrerHost: string,
  pageReferrerHost: string,
): LeadAttributionSource {
  const hosts = [httpReferrerHost, pageReferrerHost].filter(Boolean);
  if (hosts.length === 0) return "direct";
  for (const h of hosts) {
    if (isSearchHost(h)) return "organic_search";
    if (h.includes("linkedin")) return "linkedin";
  }
  return "referral";
}

export function buildLeadAttribution(input: {
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  page_referrer?: string;
  cta_id?: string;
  cta_label?: string;
  http_referer?: string | null;
}): LeadAttributionSnapshot {
  const utm_source_raw = trimField(input.utm_source, LEAD_ATTRIBUTION_LIMITS.utm);
  const utm_medium_raw = trimField(input.utm_medium, LEAD_ATTRIBUTION_LIMITS.utm);
  const utm_campaign_raw = trimField(input.utm_campaign, LEAD_ATTRIBUTION_LIMITS.utm);
  const cta_id = trimField(input.cta_id, LEAD_ATTRIBUTION_LIMITS.cta_id);
  const cta_label = trimField(input.cta_label, LEAD_ATTRIBUTION_LIMITS.cta_label);

  const httpHost = hostFromReferrerHeader(input.http_referer ?? null);
  const pageHost = hostFromPageReferrer(trimField(input.page_referrer, LEAD_ATTRIBUTION_LIMITS.referrer));
  const referrer_host = httpHost || pageHost;

  const hasUtm = Boolean(utm_source_raw || utm_medium_raw);
  const fromUtm = deriveSourceFromUtm(utm_source_raw, utm_medium_raw);
  let source: LeadAttributionSource;
  if (hasUtm) {
    source = fromUtm ?? (utm_source_raw || utm_medium_raw ? "other" : "unknown");
  } else {
    source = deriveSourceFromHosts(httpHost, pageHost);
  }

  const medium = slugMedium(utm_medium_raw);
  const campaign = slugCampaign(utm_campaign_raw);

  return {
    source,
    medium,
    campaign,
    cta_id,
    cta_label,
    utm_source_raw,
    utm_medium_raw,
    utm_campaign_raw,
    referrer_host,
  };
}

export function emptyLeadAttribution(): LeadAttributionSnapshot {
  return {
    source: "unknown",
    medium: "",
    campaign: "",
    cta_id: "",
    cta_label: "",
    utm_source_raw: "",
    utm_medium_raw: "",
    utm_campaign_raw: "",
    referrer_host: "",
  };
}

export function attributionFromOutbound(
  ob: { attribution?: LeadAttributionSnapshot | null } | null | undefined,
): LeadAttributionSnapshot {
  const a = ob?.attribution;
  if (!a || typeof a !== "object") return emptyLeadAttribution();
  const src = LEAD_ATTRIBUTION_SOURCES.includes(a.source as LeadAttributionSource)
    ? (a.source as LeadAttributionSource)
    : "unknown";
  return {
    source: src,
    medium: typeof a.medium === "string" ? a.medium : "",
    campaign: typeof a.campaign === "string" ? a.campaign : "",
    cta_id: typeof a.cta_id === "string" ? a.cta_id : "",
    cta_label: typeof a.cta_label === "string" ? a.cta_label : "",
    utm_source_raw: typeof a.utm_source_raw === "string" ? a.utm_source_raw : "",
    utm_medium_raw: typeof a.utm_medium_raw === "string" ? a.utm_medium_raw : "",
    utm_campaign_raw: typeof a.utm_campaign_raw === "string" ? a.utm_campaign_raw : "",
    referrer_host: typeof a.referrer_host === "string" ? a.referrer_host : "",
  };
}
