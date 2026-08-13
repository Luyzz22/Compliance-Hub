import { NextResponse } from "next/server";

import { serverSessionApiFetch } from "@/lib/serverBackendApi";

export async function GET() {
  const res = await serverSessionApiFetch(
    "/api/v1/ai-governance/report/board/markdown",
  );
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
