/**
 * Wave 28.2 – Pipedrive-Deal nur für qualifizierte, vertriebstaugliche Leads.
 * Geteilt zwischen Admin-UI und Server (kein server-only).
 */

/** Segmente, die auch ohne ausgefüllte Firma als deal-würdig gelten (B2B-Schwerpunkt). */
export const PIPEDRIVE_PRIORITY_SEGMENTS = ["enterprise_sap", "kanzlei_wp"] as const;

function isWeakCompanyName(name: string): boolean {
  const t = name.trim();
  if (t.length < 2) return true;
  return /^(n\/a|na|none|unknown|unbekannt|test|xxx|-+)$/i.test(t);
}

/** Bewusst `string` für Triage/Segment, damit `LeadSyncPayloadV1` und Inbox-Item passen. */
export type PipedriveEligibilityInput = {
  triage_status: string;
  owner: string;
  segment: string;
  company: string;
  business_email: string;
};

export function isLeadPipedriveDealEligible(item: PipedriveEligibilityInput): boolean {
  const email = item.business_email?.trim().toLowerCase() ?? "";
  if (!email || !email.includes("@")) return false;
  if (item.triage_status === "spam") return false;
  if (item.triage_status !== "qualified") return false;

  const companyOk = item.company.trim().length >= 2 && !isWeakCompanyName(item.company);
  const segmentOk = (PIPEDRIVE_PRIORITY_SEGMENTS as readonly string[]).includes(item.segment);
  const ownerOk = item.owner.trim().length > 0;

  return companyOk || segmentOk || ownerOk;
}

/** Kompakte deutsche Zeile für die Admin-UI. */
export function describePipedriveDealEligibility(item: PipedriveEligibilityInput): {
  eligible: boolean;
  summary: string;
} {
  const email = item.business_email?.trim().toLowerCase() ?? "";
  if (!email || !email.includes("@")) {
    return { eligible: false, summary: "Keine gültige Geschäfts-E-Mail." };
  }
  if (item.triage_status === "spam") {
    return { eligible: false, summary: "Als Spam markiert — kein Pipedrive-Deal." };
  }
  if (item.triage_status !== "qualified") {
    return {
      eligible: false,
      summary: `Triage ist „${item.triage_status}“ — erforderlich: „qualifiziert“.`,
    };
  }

  const companyOk = item.company.trim().length >= 2 && !isWeakCompanyName(item.company);
  const segmentOk = (PIPEDRIVE_PRIORITY_SEGMENTS as readonly string[]).includes(item.segment);
  const ownerOk = item.owner.trim().length > 0;

  if (companyOk || segmentOk || ownerOk) {
    const parts: string[] = [];
    if (companyOk) parts.push("Firma");
    if (segmentOk) parts.push(`Segment ${item.segment}`);
    if (ownerOk) parts.push("Owner gesetzt");
    return {
      eligible: true,
      summary: `Deal-würdig (${parts.join(", ")}). HubSpot bleibt Kontakt-/Historie-System.`,
    };
  }

  return {
    eligible: false,
    summary:
      "Qualifiziert, aber ohne belastbare Firma, ohne Prioritäts-Segment (enterprise_sap / kanzlei_wp) und ohne Owner.",
  };
}
