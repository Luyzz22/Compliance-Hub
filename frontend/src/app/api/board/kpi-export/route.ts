import { NextRequest, NextResponse } from "next/server";

import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

const API_BASE =
  process.env.COMPLIANCEHUB_API_BASE_URL || "http://localhost:8000";
const API_KEY =
  process.env.COMPLIANCEHUB_API_KEY || "tenant-overview-key";

export async function GET(request: NextRequest) {
  const tenantId = await getWorkspaceTenantIdServer();
  const format = request.nextUrl.searchParams.get("format") || "json";
  const validFormat = format === "csv" ? "csv" : "json";
  const url = `${API_BASE}/api/v1/ai-governance/report/board/kpi-export?format=${validFormat}`;
  const res = await fetch(url, {
    headers: {
      "x-api-key": API_KEY,
      "x-tenant-id": tenantId,
    },
    cache: "no-store",
  });
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
