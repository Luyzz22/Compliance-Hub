import { NextResponse } from "next/server";

import { buildAdvisorEvidenceHooksPortfolioDto } from "@/lib/advisorEvidenceHookBuild";
import { readAdvisorEvidenceHooks } from "@/lib/advisorEvidenceHookStore";
import { computeKanzleiPortfolioPayload } from "@/lib/kanzleiPortfolioAggregate";
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
  const omitMarkdown = url.searchParams.get("markdown") === "0";

  const now = new Date();
  const [payload, stored] = await Promise.all([
    computeKanzleiPortfolioPayload(now),
    readAdvisorEvidenceHooks(),
  ]);
  const evidence_hooks = buildAdvisorEvidenceHooksPortfolioDto(payload, stored);

  if (omitMarkdown) {
    return NextResponse.json({
      ok: true,
      evidence_hooks: { ...evidence_hooks, markdown_de: "" },
      markdown_de: null,
    });
  }

  return NextResponse.json({
    ok: true,
    evidence_hooks,
    markdown_de: evidence_hooks.markdown_de,
  });
}
