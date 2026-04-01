/**
 * Öffentliche Lead-Erfassung (Marketing / Sales).
 * Server-Handling: `app/api/lead-inquiry/route.ts`.
 */

export const LEAD_SEGMENTS = [
  { value: "industrie_mittelstand", label: "Industrie / Mittelstand" },
  { value: "kanzlei_wp", label: "Kanzlei / WP" },
  { value: "enterprise_sap", label: "Enterprise / SAP" },
  { value: "sonstiges", label: "Sonstiges" },
] as const;

export type LeadSegment = (typeof LEAD_SEGMENTS)[number]["value"];

const SEGMENT_SET = new Set<string>(LEAD_SEGMENTS.map((s) => s.value));

export function isLeadSegment(v: string): v is LeadSegment {
  return SEGMENT_SET.has(v);
}

export type LeadInquiryPayload = {
  name: string;
  work_email: string;
  company: string;
  segment: LeadSegment;
  message: string;
  source_page: string;
  /** Honeypot: muss leer sein */
  company_website?: string;
};

export const LEAD_FIELD_LIMITS = {
  name: 120,
  company: 200,
  message: 4000,
  email: 254,
  source_page: 120,
} as const;
