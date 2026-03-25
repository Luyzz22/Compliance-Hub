import { NextResponse } from "next/server";

const API_BASE =
  process.env.COMPLIANCEHUB_API_BASE_URL || "http://localhost:8000";
const DEMO_KEY = process.env.COMPLIANCEHUB_DEMO_SEED_API_KEY?.trim() || "";

export async function GET() {
  if (!DEMO_KEY) {
    return NextResponse.json(
      { error: "COMPLIANCEHUB_DEMO_SEED_API_KEY nicht gesetzt" },
      { status: 503 },
    );
  }
  const res = await fetch(`${API_BASE}/api/v1/demo/tenant-templates`, {
    headers: { "x-api-key": DEMO_KEY },
    cache: "no-store",
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
