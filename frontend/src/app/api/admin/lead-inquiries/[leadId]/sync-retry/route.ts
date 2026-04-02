import { NextResponse } from "next/server";

import { isLeadAdminAuthorized } from "@/lib/leadAdminAuth";
import { manualRetryLeadSyncJob, redactLeadSyncJobForApi } from "@/lib/leadSyncDispatcher";
import { getLeadSyncJobById } from "@/lib/leadSyncStore";

export const runtime = "nodejs";

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export async function POST(req: Request, ctx: { params: Promise<{ leadId: string }> }) {
  if (!process.env.LEAD_ADMIN_SECRET?.trim()) {
    return NextResponse.json({ error: "not_configured" }, { status: 404 });
  }
  if (!isLeadAdminAuthorized(req)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const { leadId } = await ctx.params;
  let body: { job_id?: string } = {};
  try {
    body = (await req.json()) as { job_id?: string };
  } catch {
    return NextResponse.json({ error: "invalid_json" }, { status: 400 });
  }

  const jobId = typeof body.job_id === "string" ? body.job_id.trim() : "";
  if (!jobId || !UUID_RE.test(jobId)) {
    return NextResponse.json({ error: "validation" }, { status: 400 });
  }

  const job = await getLeadSyncJobById(jobId);
  if (!job || job.lead_id !== leadId) {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }

  const updated = await manualRetryLeadSyncJob(jobId);
  return NextResponse.json({
    ok: true,
    job: updated ? redactLeadSyncJobForApi(updated) : null,
  });
}
