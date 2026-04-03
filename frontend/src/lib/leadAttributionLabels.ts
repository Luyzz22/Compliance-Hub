import type { LeadAttributionSource } from "@/lib/leadAttribution";

export const LEAD_ATTRIBUTION_SOURCE_LABELS_DE: Record<LeadAttributionSource, string> = {
  direct: "Direkt",
  organic_search: "Organische Suche",
  referral: "Referral / Website",
  linkedin: "LinkedIn",
  newsletter: "Newsletter / Liste",
  paid_search: "Bezahlte Suche",
  paid_social: "Paid Social",
  email: "E-Mail (UTM)",
  other: "Sonstige Quelle (UTM)",
  unknown: "Unbekannt (Legacy)",
};
