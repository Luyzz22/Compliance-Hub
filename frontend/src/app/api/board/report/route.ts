import { NextResponse } from "next/server";

import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

const API_BASE =
  process.env.COMPLIANCEHUB_API_BASE_URL || "http://localhost:8000";
const API_KEY =
  process.env.COMPLIANCEHUB_API_KEY || "tenant-overview-key";

export async function GET() {
  const tenantId = await getWorkspaceTenantIdServer();
  const url = `${API_BASE}/api/v1/ai-governance/report/board`;
  const res = await fetch(url, {
    headers: {
      "x-api-key": API_KEY,
      "x-tenant-id": tenantId,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    return NextResponse.json(
      { error: "Report konnte nicht geladen werden" },
      { status: res.status },
    );
  }
  const report = (await res.json()) as {
    tenant_id: string;
    generated_at: string;
    [key: string]: unknown;
  };
  const dateStr =
    report.generated_at?.slice(0, 10).replace(/-/g, "") ?? "report";
  const filename = `ai-board-report-${report.tenant_id ?? "tenant"}-${dateStr}.json`;
  const body = JSON.stringify(report);
  const headers = new Headers();
  headers.set("Content-Type", "application/json; charset=utf-8");
  headers.set(
    "Content-Disposition",
    `attachment; filename="${filename}"`,
  );
  return new NextResponse(body, { status: 200, headers });
}
