import { NextRequest, NextResponse } from "next/server";

import { readServerSecret } from "@/lib/serverSecret";
import {
  complianceApiBaseUrl,
  mutationCsrfIsValid,
  noStoreJson,
} from "@/lib/serverSession";

export async function POST(request: NextRequest) {
  if (!mutationCsrfIsValid(request)) {
    return noStoreJson({ error: "csrf_validation_failed" }, { status: 403 });
  }
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
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Ungültiger JSON-Body" }, { status: 400 });
  }
  const res = await fetch(`${complianceApiBaseUrl()}/api/v1/demo/tenants/seed`, {
    method: "POST",
    headers: {
      "x-api-key": demoKey,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
    cache: "no-store",
    redirect: "manual",
    signal: AbortSignal.timeout(30_000),
  });
  const text = await res.text();
  if (!res.ok) {
    try {
      const err = JSON.parse(text) as { detail?: string };
      return NextResponse.json(
        { error: err.detail || "Demo-Seed fehlgeschlagen" },
        { status: res.status },
      );
    } catch {
      return NextResponse.json(
        { error: "Demo-Seed fehlgeschlagen" },
        { status: res.status },
      );
    }
  }
  try {
    return NextResponse.json(JSON.parse(text) as object);
  } catch {
    return NextResponse.json({ error: "Ungültige API-Antwort" }, { status: 502 });
  }
}
