import { NextResponse } from "next/server";

import { boardReadinessBannerFromPayload, computeBoardReadinessPayload } from "@/lib/boardReadinessAggregate";
import { isLeadAdminAuthorized } from "@/lib/leadAdminAuth";

export const runtime = "nodejs";

export async function GET(req: Request) {
  if (!process.env.LEAD_ADMIN_SECRET?.trim()) {
    return NextResponse.json({ error: "not_configured" }, { status: 404 });
  }
  if (!isLeadAdminAuthorized(req)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const url = new URL(req.url);
  const bannerOnly = url.searchParams.get("banner") === "1";

  const payload = await computeBoardReadinessPayload();
  if (bannerOnly) {
    return NextResponse.json({ ok: true, board_readiness_banner: boardReadinessBannerFromPayload(payload) });
  }
  return NextResponse.json({ ok: true, board_readiness: payload });
}
