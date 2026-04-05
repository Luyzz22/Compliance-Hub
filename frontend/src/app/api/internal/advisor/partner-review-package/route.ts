import { NextResponse } from "next/server";

import { computeKanzleiPortfolioPayload } from "@/lib/kanzleiPortfolioAggregate";
import { readKanzleiMonthlyReportBaseline } from "@/lib/kanzleiMonthlyReportBaseline";
import { buildPartnerReviewPackage } from "@/lib/partnerReviewPackageBuild";
import { partnerReviewPackageMarkdownDe } from "@/lib/partnerReviewPackageMarkdown";
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
  const compare = url.searchParams.get("compare") !== "0";
  const topNRaw = url.searchParams.get("top_n");
  const attentionTopN = Math.min(15, Math.max(3, Number.parseInt(topNRaw ?? "8", 10) || 8));
  const format = url.searchParams.get("format")?.trim().toLowerCase();

  const payload = await computeKanzleiPortfolioPayload(new Date());
  const baseline = await readKanzleiMonthlyReportBaseline();

  const partner_review_package = buildPartnerReviewPackage(payload, baseline, {
    compareToBaseline: compare,
    attentionTopN,
  });
  const markdown_de = partnerReviewPackageMarkdownDe(partner_review_package);

  if (format === "markdown" || format === "md") {
    return new NextResponse(markdown_de, {
      status: 200,
      headers: {
        "Content-Type": "text/markdown; charset=utf-8",
        "Content-Disposition": `attachment; filename="partner-review-package-${partner_review_package.meta.generated_at.slice(0, 10)}.md"`,
      },
    });
  }

  return NextResponse.json({
    ok: true,
    partner_review_package,
    markdown_de,
    meta: {
      version: partner_review_package.meta.version,
      generated_at: partner_review_package.meta.generated_at,
      portfolio_generated_at: partner_review_package.meta.portfolio_generated_at,
      compared_to_baseline: partner_review_package.meta.compared_to_baseline,
    },
  });
}
