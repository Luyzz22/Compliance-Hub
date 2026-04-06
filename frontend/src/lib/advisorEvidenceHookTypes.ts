/** Wave 50 – ERP-Evidence-Hooks (metadata). */
export const ADVISOR_EVIDENCE_HOOKS_VERSION = "wave50-v1";

export type EvidenceSourceSystemType =
  | "sap_s4hana"
  | "sap_btp"
  | "datev"
  | "ms_dynamics"
  | "generic_erp";

export type EvidenceDomain =
  | "invoice"
  | "access"
  | "approval"
  | "vendor"
  | "ai_system_inventory"
  | "policy_artifact";

export type EvidenceConnectionStatus = "not_connected" | "planned" | "connected" | "error";

export type EvidenceHookStoredRecord = {
  hook_id: string;
  tenant_id: string;
  source_system_type: EvidenceSourceSystemType;
  source_label: string;
  evidence_domain: EvidenceDomain;
  connection_status: EvidenceConnectionStatus;
  last_sync_at: string | null;
  note: string | null;
};

export type EvidenceHookRowDto = {
  hook_id: string;
  tenant_id: string;
  source_system_type: EvidenceSourceSystemType;
  source_label: string;
  evidence_domain: EvidenceDomain;
  connection_status: EvidenceConnectionStatus;
  last_sync_at: string | null;
  evidence_hint_de: string;
  compliance_relevance_de: string[];
  is_synthetic: boolean;
};

export type AdvisorEvidenceHooksSummaryDto = {
  total_hook_rows: number;
  by_status: Record<EvidenceConnectionStatus, number>;
  by_source_type: Partial<Record<EvidenceSourceSystemType, number>>;
  mandanten_without_sap_touchpoint: number;
  mandanten_without_datev_export: number;
  mandanten_enterprise_upsell_candidates: number;
};

export type AdvisorEvidenceHooksMandantBlockDto = {
  tenant_id: string;
  mandant_label: string | null;
  hooks: EvidenceHookRowDto[];
  enterprise_readiness_hint_de: string;
  links: {
    mandant_export_page: string;
    datev_bundle_api: string;
    readiness_export_api: string;
    board_readiness_admin: string;
  };
};

export type AdvisorEvidenceHooksTopGapDto = {
  tenant_id: string;
  mandant_label: string | null;
  hint_de: string;
  links: AdvisorEvidenceHooksMandantBlockDto["links"];
};

export type AdvisorEvidenceHooksPortfolioDto = {
  version: typeof ADVISOR_EVIDENCE_HOOKS_VERSION;
  generated_at: string;
  portfolio_generated_at: string;
  disclaimer_de: string;
  summary: AdvisorEvidenceHooksSummaryDto;
  mandanten: AdvisorEvidenceHooksMandantBlockDto[];
  top_gaps: AdvisorEvidenceHooksTopGapDto[];
  markdown_de: string;
};
