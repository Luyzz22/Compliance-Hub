import { createHash } from "crypto";

import { isConsumerEmailDomain } from "@/lib/leadAntiAbuse";

/** Konservativ: wiederholte Anfrage derselben E-Mail (kein stiller Merge). */
export type LeadDuplicateHint = "none" | "same_email_repeat";

/**
 * Primärer Kontakt-Schlüssel: normalisierte geschäftliche E-Mail (Hash, kein Klartext im Key).
 * Stabil über alle Submissions einer Person.
 */
export function normalizeLeadEmail(email: string): string {
  return email.trim().toLowerCase();
}

/** Sekundär: Firmenname nur für Account-Gruppierung, nicht zum automatischen Zusammenführen von Kontakten. */
export function normalizeLeadCompany(company: string): string {
  return company
    .trim()
    .toLowerCase()
    .replace(/\s+/g, " ")
    .replace(/[.,;]+$/g, "")
    .trim();
}

export function extractEmailDomain(email: string): string | null {
  const at = email.lastIndexOf("@");
  if (at < 0) return null;
  return email.slice(at + 1).toLowerCase().trim() || null;
}

function sha256Hex(input: string): string {
  return createHash("sha256").update(input, "utf8").digest("hex");
}

export function buildLeadContactKey(normalizedEmail: string): string {
  return `ct_v1_${sha256Hex(`email|${normalizedEmail}`)}`;
}

/**
 * Account-/Firmen-Gruppierung (schwächer als Kontakt-Key).
 * – Bei sinnvollem Firmennamen: Hash des normalisierten Namens.
 * – Sonst: registrierte Domain, wenn nicht Consumer-Domain.
 */
export function buildLeadAccountKey(company: string, businessEmail: string): string | null {
  const co = normalizeLeadCompany(company);
  if (co.length >= 2) {
    return `ac_v1_co_${sha256Hex(`co|${co}`)}`;
  }
  const dom = extractEmailDomain(businessEmail);
  if (!dom || isConsumerEmailDomain(dom)) return null;
  return `ac_v1_dom_${dom}`;
}

export function deriveLeadContactKeyFromStoredRecord(record: {
  lead_contact_key?: string;
  outbound: { business_email: string; schema_version?: string };
}): string {
  if (record.lead_contact_key?.trim()) return record.lead_contact_key.trim();
  return buildLeadContactKey(normalizeLeadEmail(record.outbound.business_email));
}

export function deriveLeadAccountKeyFromStoredRecord(record: {
  lead_account_key?: string | null;
  outbound: { company: string; business_email: string };
}): string | null {
  if (record.lead_account_key !== undefined) {
    return record.lead_account_key;
  }
  return buildLeadAccountKey(record.outbound.company, record.outbound.business_email);
}
