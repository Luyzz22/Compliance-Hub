import { NextResponse } from "next/server";

import { readRecentLeadRecordsMerged } from "@/lib/leadPersistence";

export const runtime = "nodejs";

/**
 * Interne Übersicht gespeicherter Leads (JSON).
 * Schutz: `Authorization: Bearer <LEAD_ADMIN_SECRET>` oder Query `?secret=` (nur falls nötig).
 */
export async function GET(req: Request) {
  const secret = process.env.LEAD_ADMIN_SECRET?.trim();
  if (!secret) {
    return NextResponse.json({ error: "not_configured" }, { status: 404 });
  }

  const auth = req.headers.get("authorization");
  const url = new URL(req.url);
  const qSecret = url.searchParams.get("secret");
  const token =
    auth?.startsWith("Bearer ") ? auth.slice(7).trim() : qSecret?.trim() ?? "";
  if (token !== secret) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const limit = Math.min(
    100,
    Math.max(1, parseInt(url.searchParams.get("limit") ?? "40", 10) || 40),
  );

  const rows = await readRecentLeadRecordsMerged(limit);

  return NextResponse.json({
    ok: true,
    count: rows.length,
    items: rows.map((r) => ({
      lead_id: r.lead_id,
      trace_id: r.trace_id,
      status: r.status,
      webhook_ok: r.webhook_ok,
      webhook_at: r.webhook_at,
      webhook_error: r.webhook_error,
      created_at: r.created_at,
      segment: r.outbound.segment,
      route_key: r.outbound.route.route_key,
      queue_label: r.outbound.route.queue_label,
      source_page: r.outbound.source_page,
      company: r.outbound.company,
      business_email: r.outbound.business_email,
      name: r.outbound.name,
      message_preview: r.outbound.message.slice(0, 280),
    })),
  });
}
