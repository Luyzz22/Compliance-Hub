import { NextResponse } from "next/server";

import { serverSessionApiFetch } from "@/lib/serverBackendApi";

export async function GET() {
  const res = await serverSessionApiFetch(
    "/api/v1/ai-governance/report/board",
  );
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
