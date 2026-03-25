import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
  featureAdvisorClientSnapshot,
  featureAdvisorWorkspace,
  featureAiActDocs,
  featureAiGovernancePlaybook,
  featureCrossRegulationDashboard,
  featureAiComplianceBoardReport,
  featureCrossRegulationLlmAssist,
  featureAiKpiKri,
  featureAiGovernanceSetupWizard,
  featureApiKeysUi,
  featureDemoSeeding,
  featureEvidencePreviewBadge,
  featureEvidenceUploads,
  featureGuidedSetup,
  featureLlmActionDrafts,
  featureLlmEnabled,
  featureLlmExplain,
  featureLlmKpiSuggestions,
  featurePilotRunbook,
  featureReadinessScore,
  featureWhatIfSimulator,
} from "./config";

const envKeys = [
  "NEXT_PUBLIC_FEATURE_ADVISOR_WORKSPACE",
  "NEXT_PUBLIC_FEATURE_ADVISOR_CLIENT_SNAPSHOT",
  "NEXT_PUBLIC_FEATURE_READINESS_SCORE",
  "NEXT_PUBLIC_FEATURE_DEMO_SEEDING",
  "NEXT_PUBLIC_FEATURE_EVIDENCE_UPLOADS",
  "NEXT_PUBLIC_FEATURE_GUIDED_SETUP",
  "NEXT_PUBLIC_FEATURE_EVIDENCE_PREVIEW_BADGE",
  "NEXT_PUBLIC_FEATURE_PILOT_RUNBOOK",
  "NEXT_PUBLIC_FEATURE_API_KEYS_UI",
  "NEXT_PUBLIC_FEATURE_AI_ACT_DOCS",
  "NEXT_PUBLIC_FEATURE_WHAT_IF_SIMULATOR",
  "NEXT_PUBLIC_FEATURE_AI_GOVERNANCE_PLAYBOOK",
  "NEXT_PUBLIC_FEATURE_CROSS_REGULATION_DASHBOARD",
  "NEXT_PUBLIC_FEATURE_CROSS_REGULATION_LLM_ASSIST",
  "NEXT_PUBLIC_FEATURE_AI_COMPLIANCE_BOARD_REPORT",
  "NEXT_PUBLIC_FEATURE_AI_KPI_KRI",
  "NEXT_PUBLIC_FEATURE_AI_GOVERNANCE_SETUP_WIZARD",
  "NEXT_PUBLIC_FEATURE_LLM_ENABLED",
  "NEXT_PUBLIC_FEATURE_LLM_KPI_SUGGESTIONS",
  "NEXT_PUBLIC_FEATURE_LLM_EXPLAIN",
  "NEXT_PUBLIC_FEATURE_LLM_ACTION_DRAFTS",
] as const;

describe("feature flags from env", () => {
  const saved: Partial<Record<(typeof envKeys)[number], string | undefined>> = {};

  beforeEach(() => {
    for (const k of envKeys) {
      saved[k] = process.env[k];
    }
  });

  afterEach(() => {
    for (const k of envKeys) {
      const v = saved[k];
      if (v === undefined) {
        delete process.env[k];
      } else {
        process.env[k] = v;
      }
    }
  });

  it("defaults to enabled when variables are unset", () => {
    for (const k of envKeys) {
      delete process.env[k];
    }
    expect(featureAdvisorWorkspace()).toBe(true);
    expect(featureAdvisorClientSnapshot()).toBe(true);
    expect(featureReadinessScore()).toBe(true);
    expect(featureDemoSeeding()).toBe(true);
    expect(featureEvidenceUploads()).toBe(true);
    expect(featureGuidedSetup()).toBe(true);
    expect(featureEvidencePreviewBadge()).toBe(false);
    expect(featurePilotRunbook()).toBe(true);
    expect(featureApiKeysUi()).toBe(true);
    expect(featureLlmEnabled()).toBe(false);
    expect(featureLlmKpiSuggestions()).toBe(false);
    expect(featureLlmExplain()).toBe(false);
    expect(featureLlmActionDrafts()).toBe(false);
    expect(featureAiActDocs()).toBe(true);
    expect(featureWhatIfSimulator()).toBe(true);
    expect(featureAiGovernancePlaybook()).toBe(true);
    expect(featureCrossRegulationDashboard()).toBe(true);
    expect(featureCrossRegulationLlmAssist()).toBe(true);
    expect(featureAiComplianceBoardReport()).toBe(true);
    expect(featureAiKpiKri()).toBe(true);
    expect(featureAiGovernanceSetupWizard()).toBe(true);
  });

  it("parses common false/true tokens", () => {
    process.env.NEXT_PUBLIC_FEATURE_ADVISOR_WORKSPACE = "0";
    process.env.NEXT_PUBLIC_FEATURE_DEMO_SEEDING = "off";
    expect(featureAdvisorWorkspace()).toBe(false);
    expect(featureDemoSeeding()).toBe(false);
    process.env.NEXT_PUBLIC_FEATURE_EVIDENCE_UPLOADS = "yes";
    expect(featureEvidenceUploads()).toBe(true);
  });
});
