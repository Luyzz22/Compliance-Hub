import { NextResponse } from "next/server";

import {
  WORKSPACE_GOVERNANCE_FEATURES,
  type WorkspaceGovernanceFeatureName,
} from "@/lib/workspaceTelemetry";

const API_BASE =
  process.env.COMPLIANCEHUB_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://localhost:8000";
const API_KEY =
  process.env.COMPLIANCEHUB_API_KEY ||
  process.env.NEXT_PUBLIC_API_KEY ||
  "tenant-overview-key";

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

export async function POST(req: Request) {
  let parsed: Body;
  try {
    parsed = (await req.json()) as Body;
  } catch {
    return NextResponse.json({ ok: false }, { status: 400 });
  }

  const tenantId = typeof parsed.tenant_id === "string" ? parsed.tenant_id.trim() : "";
  const featureName = typeof parsed.feature_name === "string" ? parsed.feature_name.trim() : "";
  if (!tenantId || !featureName || !ALLOWED.has(featureName)) {
    return NextResponse.json({ ok: false }, { status: 400 });
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

  const url = `${API_BASE}/api/v1/workspace/feature-used?${params.toString()}`;
  try {
    await fetch(url, {
      method: "GET",
      headers: {
        "x-api-key": API_KEY,
        "x-tenant-id": tenantId,
      },
      cache: "no-store",
    });
  } catch {
    /* Proxy bleibt best-effort */
  }

  return NextResponse.json({ ok: true });
}
