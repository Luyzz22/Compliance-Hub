import { NextResponse } from "next/server";

import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

const API_BASE =
  process.env.COMPLIANCEHUB_API_BASE_URL || "http://localhost:8000";
const API_KEY =
  process.env.COMPLIANCEHUB_API_KEY || "tenant-overview-key";

export async function GET() {
  const tenantId = await getWorkspaceTenantIdServer();
  const url = `${API_BASE}/api/v1/ai-governance/report/board/markdown`;
  const res = await fetch(url, {
    headers: {
      "x-api-key": API_KEY,
      "x-tenant-id": tenantId,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    return NextResponse.json(
      { error: "Markdown-Report konnte nicht geladen werden" },
      { status: res.status },
    );
  }
  const body = await res.text();
  const contentDisposition = res.headers.get("content-disposition");
  const headers = new Headers();
  headers.set("Content-Type", "text/markdown; charset=utf-8");
  if (contentDisposition) headers.set("Content-Disposition", contentDisposition);
  return new NextResponse(body, { status: 200, headers });
}
