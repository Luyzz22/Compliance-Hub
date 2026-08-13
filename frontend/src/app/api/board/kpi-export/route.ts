import { NextRequest, NextResponse } from "next/server";

import { serverSessionApiFetch } from "@/lib/serverBackendApi";

export async function GET(request: NextRequest) {
  const format = request.nextUrl.searchParams.get("format") || "json";
  const validFormat = format === "csv" ? "csv" : "json";
  const res = await serverSessionApiFetch(
    `/api/v1/ai-governance/report/board/kpi-export?format=${validFormat}`,
  );
  if (!res.ok) {
    return NextResponse.json(
      { error: "KPI-Export fehlgeschlagen" },
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
