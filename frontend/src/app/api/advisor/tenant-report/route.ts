import { NextRequest, NextResponse } from "next/server";

import { serverSessionApiFetch } from "@/lib/serverBackendApi";

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
  const res = await serverSessionApiFetch(
    `/api/v1/advisors/${aid}/tenants/${tid}/report?format=${format}`,
  );
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
