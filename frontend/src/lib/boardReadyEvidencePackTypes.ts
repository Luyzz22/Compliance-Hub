/**
 * Wave 51 – Board-Ready Evidence Pack (Geschäftsführungs-/Board-nahe Kurzfassung, Markdown-first).
 */

export const BOARD_READY_EVIDENCE_PACK_VERSION = "wave51-v1";

export type BoardReadyEvidencePackMeta = {
  version: typeof BOARD_READY_EVIDENCE_PACK_VERSION;
  generated_at: string;
  portfolio_version: string;
  portfolio_generated_at: string;
  /** Welche Signalquellen eingeflossen sind (Nachvollziehbarkeit). */
  included_signals_de: string[];
  disclaimer_de: string;
};

export type BoardReadyEvidencePackSectionA = {
  overall_posture_de: string;
  top_risks_de: string[];
  major_open_items_de: string[];
};

export type BoardReadyCrossRegHighlight = {
  pillar_label_de: string;
  summary_de: string;
};

export type BoardReadyEvidencePackSectionB = {
  highlights: BoardReadyCrossRegHighlight[];
  multi_stress_note_de: string | null;
};

export type BoardReadyEvidencePackSectionC = {
  ai_act_relevance_note_de: string;
  governance_gaps_de: string[];
  oversight_monitoring_de: string;
};

export type BoardReadyEvidencePackSectionD = {
  executive_summary_de: string;
  datev_erp_note_de: string;
  status_overview_de: string;
};

export type BoardReadyEvidencePackSectionE = {
  actions_de: string[];
};

export type BoardReadyEvidencePackDto = {
  meta: BoardReadyEvidencePackMeta;
  section_a_executive_snapshot: BoardReadyEvidencePackSectionA;
  section_b_cross_regulation: BoardReadyEvidencePackSectionB;
  section_c_ai_governance: BoardReadyEvidencePackSectionC;
  section_d_evidence_touchpoints: BoardReadyEvidencePackSectionD;
  section_e_next_actions: BoardReadyEvidencePackSectionE;
  markdown_de: string;
};
