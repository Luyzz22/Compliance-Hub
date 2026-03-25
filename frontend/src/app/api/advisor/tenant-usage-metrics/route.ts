import { NextRequest, NextResponse } from "next/server";

const API_BASE =
  process.env.COMPLIANCEHUB_API_BASE_URL || "http://localhost:8000";
const API_KEY = process.env.COMPLIANCEHUB_API_KEY || "tenant-overview-key";

export async function GET(request: NextRequest) {
  const tenantId = request.nextUrl.searchParams.get("tenantId")?.trim();
  const advisorId =
    request.nextUrl.searchParams.get("advisorId")?.trim() ||
    process.env.COMPLIANCEHUB_ADVISOR_ID?.trim() ||
    "";

  if (!tenantId || !advisorId) {
    return NextResponse.json(
      { error: "tenantId und advisorId erforderlich" },
      { status: 400 },
    );
  }

  const aid = encodeURIComponent(advisorId);
  const tid = encodeURIComponent(tenantId);
  const url = `${API_BASE}/api/v1/advisors/${aid}/tenants/${tid}/usage-metrics`;
  const res = await fetch(url, {
    headers: {
      "x-api-key": API_KEY,
      "x-advisor-id": advisorId,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const detail = (await res.json().catch(() => ({}))) as { detail?: string };
    return NextResponse.json(
      { error: detail.detail || "Nutzungsmetriken konnten nicht geladen werden" },
      { status: res.status },
    );
  }
  const data = await res.json();
  return NextResponse.json(data);
}
