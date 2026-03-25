import { NextRequest, NextResponse } from "next/server";

const API_BASE =
  process.env.COMPLIANCEHUB_API_BASE_URL || "http://localhost:8000";
const DEMO_KEY = process.env.COMPLIANCEHUB_DEMO_SEED_API_KEY?.trim() || "";

export async function POST(request: NextRequest) {
  if (!DEMO_KEY) {
    return NextResponse.json(
      { error: "COMPLIANCEHUB_DEMO_SEED_API_KEY nicht gesetzt" },
      { status: 503 },
    );
  }
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Ungültiger JSON-Body" }, { status: 400 });
  }
  const res = await fetch(`${API_BASE}/api/v1/demo/tenants/seed`, {
    method: "POST",
    headers: {
      "x-api-key": DEMO_KEY,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
    cache: "no-store",
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
