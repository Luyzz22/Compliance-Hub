/** Muss mit GET /workspace/tenant-meta workspace_mode übereinstimmen (Client-Spiegel für Audits). */
export type WorkspaceTelemetryMode = "production" | "demo" | "playground";

/** Kanonische Governance-View-Keys (Dashboards / Audits). */
export const WORKSPACE_GOVERNANCE_FEATURES = [
  "playbook_overview",
  "cross_regulation_summary",
  "board_reports_overview",
  "ai_system_detail",
] as const;

export type WorkspaceGovernanceFeatureName = (typeof WORKSPACE_GOVERNANCE_FEATURES)[number];

export type TrackWorkspaceFeatureUsedArgs = {
  tenantId: string;
  workspaceMode: WorkspaceTelemetryMode;
  featureName: WorkspaceGovernanceFeatureName;
  aiSystemId?: string;
  frameworkKey?: string;
  routeName?: string;
};

type TelemetryExtraKey = "ai_system_id" | "framework_key" | "route_name";

const DEBOUNCE_MS = 1600;
const inflight = new Map<string, number>();

/** Nur für Unit-Tests (Debouncing ist pro Modulinstanz). */
export function resetWorkspaceTelemetryDebounceForTests(): void {
  inflight.clear();
}

function debounceKey(args: TrackWorkspaceFeatureUsedArgs): string {
  return `${args.tenantId}\0${args.featureName}\0${args.routeName ?? ""}\0${args.aiSystemId ?? ""}`;
}

/**
 * Fire-and-forget: POST auf Same-Origin-Proxy → GET /api/v1/workspace/feature-used.
 * Keine PII: nur erlaubte, optionale technische Felder.
 */
export async function trackWorkspaceFeatureUsed(args: TrackWorkspaceFeatureUsedArgs): Promise<void> {
  const key = debounceKey(args);
  const now = Date.now();
  const last = inflight.get(key) ?? 0;
  if (now - last < DEBOUNCE_MS) {
    return;
  }
  inflight.set(key, now);

  const body: {
    tenant_id: string;
    feature_name: WorkspaceGovernanceFeatureName;
    workspace_mode: WorkspaceTelemetryMode;
  } & Partial<Record<TelemetryExtraKey, string>> = {
    tenant_id: args.tenantId,
    feature_name: args.featureName,
    workspace_mode: args.workspaceMode,
  };
  if (args.aiSystemId?.trim()) {
    body.ai_system_id = args.aiSystemId.trim();
  }
  if (args.frameworkKey?.trim()) {
    body.framework_key = args.frameworkKey.trim();
  }
  if (args.routeName?.trim()) {
    body.route_name = args.routeName.trim();
  }

  try {
    await fetch("/api/workspace/feature-used", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });
  } catch {
    /* bewusst verschlucken */
  }
}
