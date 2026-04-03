/**
 * First-Touch-UTM in sessionStorage (Tab-Session), first-party, kein Cookie.
 * Nur aus URL-Parametern; wird beim Absenden der Kontaktanfrage mitgeschickt.
 */

import { LEAD_ATTRIBUTION_LIMITS } from "@/lib/leadAttribution";

export const SESSION_ATTRIBUTION_STORAGE_KEY = "ch_gtm_attr_v1";

export type SessionAttributionPayload = {
  utm_source: string;
  utm_medium: string;
  utm_campaign: string;
  first_landing_path: string;
  captured_at: string;
};

export function tryCaptureUtmFromSearchParams(sp: URLSearchParams, pathname: string): void {
  if (typeof window === "undefined") return;
  const u = sp.get("utm_source")?.trim() ?? "";
  const m = sp.get("utm_medium")?.trim() ?? "";
  const c = sp.get("utm_campaign")?.trim() ?? "";
  if (!u && !m && !c) return;
  if (sessionStorage.getItem(SESSION_ATTRIBUTION_STORAGE_KEY)) return;
  const payload: SessionAttributionPayload = {
    utm_source: u.slice(0, LEAD_ATTRIBUTION_LIMITS.utm),
    utm_medium: m.slice(0, LEAD_ATTRIBUTION_LIMITS.utm),
    utm_campaign: c.slice(0, LEAD_ATTRIBUTION_LIMITS.utm),
    first_landing_path: pathname.slice(0, 200),
    captured_at: new Date().toISOString(),
  };
  try {
    sessionStorage.setItem(SESSION_ATTRIBUTION_STORAGE_KEY, JSON.stringify(payload));
  } catch {
    /* Speicher voll / private mode */
  }
}

export function readSessionAttribution(): SessionAttributionPayload | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(SESSION_ATTRIBUTION_STORAGE_KEY);
    if (!raw) return null;
    const o = JSON.parse(raw) as Partial<SessionAttributionPayload>;
    if (typeof o !== "object" || !o) return null;
    return {
      utm_source: typeof o.utm_source === "string" ? o.utm_source : "",
      utm_medium: typeof o.utm_medium === "string" ? o.utm_medium : "",
      utm_campaign: typeof o.utm_campaign === "string" ? o.utm_campaign : "",
      first_landing_path: typeof o.first_landing_path === "string" ? o.first_landing_path : "",
      captured_at: typeof o.captured_at === "string" ? o.captured_at : "",
    };
  } catch {
    return null;
  }
}
