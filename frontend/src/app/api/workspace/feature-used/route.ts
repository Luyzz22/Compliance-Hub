import type { NextRequest } from "next/server";

import { serverSessionApiFetch } from "@/lib/serverBackendApi";
import { mutationCsrfIsValid, noStoreJson } from "@/lib/serverSession";
import {
  WORKSPACE_GOVERNANCE_FEATURES,
  type WorkspaceGovernanceFeatureName,
} from "@/lib/workspaceTelemetry";

const ALLOWED = new Set<string>(WORKSPACE_GOVERNANCE_FEATURES);

type Body = {
  tenant_id?: string;
  feature_name?: string;
  workspace_mode?: string;
  ai_system_id?: string;
  framework_key?: string;
  route_name?: string;
  [key: string]: unknown;
};

export async function POST(req: NextRequest) {
  if (!mutationCsrfIsValid(req)) {
    return noStoreJson({ ok: false, error: "csrf_validation_failed" }, { status: 403 });
  }
  let parsed: Body;
  try {
    parsed = (await req.json()) as Body;
  } catch {
    return noStoreJson({ ok: false }, { status: 400 });
  }

  const tenantId = typeof parsed.tenant_id === "string" ? parsed.tenant_id.trim() : "";
  const featureName = typeof parsed.feature_name === "string" ? parsed.feature_name.trim() : "";
  if (!tenantId || !featureName || !ALLOWED.has(featureName)) {
    return noStoreJson({ ok: false }, { status: 400 });
  }

  const params = new URLSearchParams({ feature_key: featureName as WorkspaceGovernanceFeatureName });
  const ai = typeof parsed.ai_system_id === "string" ? parsed.ai_system_id.trim() : "";
  const fw = typeof parsed.framework_key === "string" ? parsed.framework_key.trim() : "";
  const route = typeof parsed.route_name === "string" ? parsed.route_name.trim() : "";
  if (ai) {
    params.set("ai_system_id", ai);
  }
  if (fw) {
    params.set("framework_key", fw);
  }
  if (route) {
    params.set("route_name", route);
  }

  try {
    const backend = await serverSessionApiFetch(
      `/api/v1/workspace/feature-used?${params.toString()}`,
    );
    if (!backend.ok) {
      return noStoreJson({ ok: false }, { status: backend.status });
    }
  } catch {
    return noStoreJson({ ok: false }, { status: 503 });
  }

  return noStoreJson({ ok: true });
}
