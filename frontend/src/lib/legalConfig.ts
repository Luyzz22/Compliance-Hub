import "server-only";

export type LegalConfig = {
  entityName: string;
  representative: string;
  street: string;
  postalCode: string;
  city: string;
  country: string;
  email: string;
  phone?: string;
  registerCourt: string;
  registerNumber: string;
  vatId: string;
  privacyEmail: string;
  dpoContact?: string;
  privacyNoticeVersion: string;
  privacyReviewedAt: string;
  logRetentionDays: string;
  leadRetentionDays: string;
};

const requiredKeys = {
  entityName: "COMPLIANCEHUB_LEGAL_ENTITY_NAME",
  representative: "COMPLIANCEHUB_LEGAL_REPRESENTATIVE",
  street: "COMPLIANCEHUB_LEGAL_STREET",
  postalCode: "COMPLIANCEHUB_LEGAL_POSTAL_CODE",
  city: "COMPLIANCEHUB_LEGAL_CITY",
  country: "COMPLIANCEHUB_LEGAL_COUNTRY",
  email: "COMPLIANCEHUB_LEGAL_EMAIL",
  registerCourt: "COMPLIANCEHUB_LEGAL_REGISTER_COURT",
  registerNumber: "COMPLIANCEHUB_LEGAL_REGISTER_NUMBER",
  vatId: "COMPLIANCEHUB_LEGAL_VAT_ID",
  privacyEmail: "COMPLIANCEHUB_PRIVACY_EMAIL",
  privacyNoticeVersion: "COMPLIANCEHUB_PRIVACY_NOTICE_VERSION",
  privacyReviewedAt: "COMPLIANCEHUB_PRIVACY_REVIEWED_AT",
  logRetentionDays: "COMPLIANCEHUB_PRIVACY_LOG_RETENTION_DAYS",
  leadRetentionDays: "COMPLIANCEHUB_PRIVACY_LEAD_RETENTION_DAYS",
} as const;

export function legalPublishingReady(): boolean {
  return process.env.COMPLIANCEHUB_LEGAL_PUBLISH_READY === "true";
}

export function getLegalConfig(): LegalConfig | null {
  if (!legalPublishingReady()) return null;
  const values: Record<string, string> = {};
  const missing: string[] = [];
  for (const [property, key] of Object.entries(requiredKeys)) {
    const value = process.env[key]?.trim();
    if (!value) missing.push(key);
    else values[property] = value;
  }
  if (missing.length) {
    throw new Error(`Legal publishing is enabled but values are missing: ${missing.join(", ")}`);
  }
  return {
    ...(values as Omit<LegalConfig, "phone" | "dpoContact">),
    phone: process.env.COMPLIANCEHUB_LEGAL_PHONE?.trim() || undefined,
    dpoContact: process.env.COMPLIANCEHUB_PRIVACY_DPO_CONTACT?.trim() || undefined,
  };
}
