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

export function featureDemoSeeding(): boolean {
  return envBool(process.env.NEXT_PUBLIC_FEATURE_DEMO_SEEDING, true);
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
