import { NextResponse } from "next/server";

import { readServerSecret } from "@/lib/serverSecret";
import { complianceApiBaseUrl } from "@/lib/serverSession";

export async function GET() {
  const demoKey = readServerSecret({
    environmentVariable: "COMPLIANCEHUB_DEMO_SEED_API_KEY",
    fileEnvironmentVariable: "COMPLIANCEHUB_DEMO_SEED_API_KEY_FILE",
    minimumBytes: 32,
  });
  if (!demoKey) {
    return NextResponse.json(
      { error: "Demo-Seeding ist nicht freigeschaltet" },
      { status: 503 },
    );
  }
  const res = await fetch(`${complianceApiBaseUrl()}/api/v1/demo/tenant-templates`, {
    headers: { "x-api-key": demoKey },
    cache: "no-store",
    redirect: "manual",
    signal: AbortSignal.timeout(10_000),
  });
  if (!res.ok) {
    return NextResponse.json(
      { error: "Templates konnten nicht geladen werden" },
      { status: res.status },
    );
  }
  const data = await res.json();
  return NextResponse.json(data);
}
