export type AdvisorMandantHistoryEntry = {
  tenant_id: string;
  last_mandant_readiness_export_at: string | null;
  last_datev_bundle_export_at: string | null;
  last_review_marked_at: string | null;
  last_review_note_de: string | null;
};

export type AdvisorMandantHistoryState = {
  entries: AdvisorMandantHistoryEntry[];
};
