/**
 * Build-Zeit / Client: NEXT_PUBLIC_FEATURE_* (Pilot vs. Produktion).
 * "true" wenn Variable fehlt → bestehende Demos funktionieren ohne .env-Anpassung.
 */
function envBool(value: string | undefined, defaultValue: boolean): boolean {
  if (value === undefined || value === "") {
    return defaultValue;
  }
  const v = value.trim().toLowerCase();
  if (v === "0" || v === "false" || v === "no" || v === "off") {
    return false;
  }
  if (v === "1" || v === "true" || v === "yes" || v === "on") {
    return true;
  }
  return defaultValue;
}

export function featureAdvisorWorkspace(): boolean {
  return envBool(process.env.NEXT_PUBLIC_FEATURE_ADVISOR_WORKSPACE, true);
}

/** Mandanten-Governance-Snapshot im Berater-Portfolio (Backend COMPLIANCEHUB_FEATURE_ADVISOR_CLIENT_SNAPSHOT). */
export function featureAdvisorClientSnapshot(): boolean {
  return envBool(process.env.NEXT_PUBLIC_FEATURE_ADVISOR_CLIENT_SNAPSHOT, true);
}

/** AI & Compliance Readiness Score (Backend COMPLIANCEHUB_FEATURE_READINESS_SCORE). */
export function featureReadinessScore(): boolean {
  return envBool(process.env.NEXT_PUBLIC_FEATURE_READINESS_SCORE, true);
}

/** Governance Maturity Lens: GAI + OAMI im Portfolio u. a. (Backend COMPLIANCEHUB_FEATURE_GOVERNANCE_MATURITY). */
export function featureGovernanceMaturity(): boolean {
  return envBool(process.env.NEXT_PUBLIC_FEATURE_GOVERNANCE_MATURITY, true);
}

export function featureDemoSeeding(): boolean {
  return envBool(process.env.NEXT_PUBLIC_FEATURE_DEMO_SEEDING, true);
}

/** Demo-/Playground-UI: Banner, Demo-Guide, Hinweise (Backend COMPLIANCEHUB_FEATURE_DEMO_MODE). */
export function featureDemoMode(): boolean {
  return envBool(process.env.NEXT_PUBLIC_FEATURE_DEMO_MODE, false);
}

export function featureEvidenceUploads(): boolean {
  return envBool(process.env.NEXT_PUBLIC_FEATURE_EVIDENCE_UPLOADS, true);
}

export function featureGuidedSetup(): boolean {
  return envBool(process.env.NEXT_PUBLIC_FEATURE_GUIDED_SETUP, true);
}

/** Optionales UI-Badge für Evidence-Bereiche (Preview-Kennzeichnung). */
export function featureEvidencePreviewBadge(): boolean {
  return envBool(process.env.NEXT_PUBLIC_FEATURE_EVIDENCE_PREVIEW_BADGE, false);
}

/** Pilot-Runbook-Seite und Verlinkungen (Kunden-Workspace). */
export function featurePilotRunbook(): boolean {
  return envBool(process.env.NEXT_PUBLIC_FEATURE_PILOT_RUNBOOK, true);
}

/** API-Key-Verwaltung unter Einstellungen. */
export function featureApiKeysUi(): boolean {
  return envBool(process.env.NEXT_PUBLIC_FEATURE_API_KEYS_UI, true);
}

/** Globaler Schalter für LLM-/Router-Funktionen (Client-Hinweise; Backend erzwingt separat). */
export function featureLlmEnabled(): boolean {
  return envBool(process.env.NEXT_PUBLIC_FEATURE_LLM_ENABLED, false);
}

export function featureLlmLegalReasoning(): boolean {
  return envBool(process.env.NEXT_PUBLIC_FEATURE_LLM_LEGAL_REASONING, false);
}

export function featureLlmReportAssistant(): boolean {
  return envBool(process.env.NEXT_PUBLIC_FEATURE_LLM_REPORT_ASSISTANT, false);
}

export function featureLlmKpiSuggestions(): boolean {
  return envBool(process.env.NEXT_PUBLIC_FEATURE_LLM_KPI_SUGGESTIONS, false);
}

export function featureLlmExplain(): boolean {
  return envBool(process.env.NEXT_PUBLIC_FEATURE_LLM_EXPLAIN, false);
}

export function featureLlmActionDrafts(): boolean {
  return envBool(process.env.NEXT_PUBLIC_FEATURE_LLM_ACTION_DRAFTS, false);
}

/** EU-AI-Act-Dokumentation pro High-Risk-System (Backend COMPLIANCEHUB_FEATURE_AI_ACT_DOCS). */
export function featureAiActDocs(): boolean {
  return envBool(process.env.NEXT_PUBLIC_FEATURE_AI_ACT_DOCS, true);
}

/** AI-Act-Evidence-UI (Backend COMPLIANCEHUB_FEATURE_AI_ACT_EVIDENCE_VIEWS); zusätzlich tenant-meta + OPA. */
export function featureAiActEvidenceViews(): boolean {
  return envBool(process.env.NEXT_PUBLIC_FEATURE_AI_ACT_EVIDENCE_VIEWS, true);
}

/** Board-What-if-Simulator (Backend COMPLIANCEHUB_FEATURE_WHAT_IF_SIMULATOR). */
export function featureWhatIfSimulator(): boolean {
  return envBool(process.env.NEXT_PUBLIC_FEATURE_WHAT_IF_SIMULATOR, true);
}

/** AI-Governance-Playbook im Tenant-Workspace (Backend COMPLIANCEHUB_FEATURE_AI_GOVERNANCE_PLAYBOOK). */
export function featureAiGovernancePlaybook(): boolean {
  return envBool(process.env.NEXT_PUBLIC_FEATURE_AI_GOVERNANCE_PLAYBOOK, true);
}

/** Cross-Regulation-Dashboard / Regelwerksgraph (Backend COMPLIANCEHUB_FEATURE_CROSS_REGULATION_DASHBOARD). */
export function featureCrossRegulationDashboard(): boolean {
  return envBool(process.env.NEXT_PUBLIC_FEATURE_CROSS_REGULATION_DASHBOARD, true);
}

/** KI-Gap-Assist im Cross-Regulation-Dashboard (Backend COMPLIANCEHUB_FEATURE_CROSS_REGULATION_LLM_ASSIST). */
export function featureCrossRegulationLlmAssist(): boolean {
  return envBool(process.env.NEXT_PUBLIC_FEATURE_CROSS_REGULATION_LLM_ASSIST, true);
}

/** AI Compliance Board-Report (Backend COMPLIANCEHUB_FEATURE_AI_COMPLIANCE_BOARD_REPORT). */
export function featureAiComplianceBoardReport(): boolean {
  return envBool(process.env.NEXT_PUBLIC_FEATURE_AI_COMPLIANCE_BOARD_REPORT, true);
}

/** AI-KPI/KRI je KI-System und Portfolio-Summary (Backend COMPLIANCEHUB_FEATURE_AI_KPI_KRI). */
export function featureAiKpiKri(): boolean {
  return envBool(process.env.NEXT_PUBLIC_FEATURE_AI_KPI_KRI, true);
}

/** Geführtes AI-Governance-Setup (Enterprise/Berater), Backend COMPLIANCEHUB_FEATURE_AI_GOVERNANCE_SETUP_WIZARD. */
export function featureAiGovernanceSetupWizard(): boolean {
  return envBool(process.env.NEXT_PUBLIC_FEATURE_AI_GOVERNANCE_SETUP_WIZARD, true);
}
