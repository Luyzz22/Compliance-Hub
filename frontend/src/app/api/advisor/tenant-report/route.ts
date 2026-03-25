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
  const formatParam = request.nextUrl.searchParams.get("format") || "json";
  const format = formatParam === "markdown" ? "markdown" : "json";

  if (!tenantId || !advisorId) {
    return NextResponse.json(
      { error: "tenantId und advisorId erforderlich" },
      { status: 400 },
    );
  }

  const aid = encodeURIComponent(advisorId);
  const tid = encodeURIComponent(tenantId);
  const url = `${API_BASE}/api/v1/advisors/${aid}/tenants/${tid}/report?format=${format}`;
  const res = await fetch(url, {
    headers: {
      "x-api-key": API_KEY,
      "x-advisor-id": advisorId,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    return NextResponse.json(
      { error: "Mandanten-Steckbrief konnte nicht geladen werden" },
      { status: res.status },
    );
  }
  const body = await res.arrayBuffer();
  const contentType = res.headers.get("content-type") || "application/json";
  const contentDisposition = res.headers.get("content-disposition");
  const headers = new Headers();
  headers.set("Content-Type", contentType);
  if (contentDisposition) headers.set("Content-Disposition", contentDisposition);
  return new NextResponse(body, { status: 200, headers });
}
