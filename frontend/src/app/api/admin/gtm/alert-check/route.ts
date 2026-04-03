import { NextResponse } from "next/server";

import { computeGtmDashboardSnapshot } from "@/lib/gtmDashboardAggregate";
import { dispatchGtmAlertFindings } from "@/lib/gtmAlertDispatcher";
import { evaluateGtmAlertsFromSnapshot } from "@/lib/gtmAlertEvaluator";
import { isLeadAdminOrGtmAlertSecretAuthorized } from "@/lib/leadAdminAuth";

export const runtime = "nodejs";

function findingsSummaryDe(findings: { severity: string; message_de: string }[]): string {
  if (findings.length === 0) return "GTM Alert-Check: keine Schwellenverletzungen.";
  const lines = findings.map((f) => `[${f.severity}] ${f.message_de}`);
  return `GTM Alert-Check (${findings.length}):\n${lines.join("\n")}`;
}

/**
 * GET/POST für Cron (n8n, GitHub Actions): Bearer LEAD_ADMIN_SECRET oder GTM_ALERT_SECRET.
 * Bei ausgelösten Alerts: Log + optional GTM_ALERT_WEBHOOK_URL.
 */
export async function GET(req: Request) {
  return runAlertCheck(req);
}

export async function POST(req: Request) {
  return runAlertCheck(req);
}

async function runAlertCheck(req: Request) {
  if (!process.env.LEAD_ADMIN_SECRET?.trim()) {
    return NextResponse.json({ error: "not_configured" }, { status: 404 });
  }
  if (!isLeadAdminOrGtmAlertSecretAuthorized(req)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const snapshot = await computeGtmDashboardSnapshot();
  const findings = evaluateGtmAlertsFromSnapshot(snapshot);
  const critical = findings.filter((f) => f.severity === "critical");
  const warning = findings.filter((f) => f.severity === "warning");

  const summary_de = findingsSummaryDe(findings);
  const fired = findings.length > 0;

  if (fired) {
    await dispatchGtmAlertFindings({
      generated_at: snapshot.generated_at,
      findings,
      summary_de,
      health_snapshot_url_hint: "GET /api/admin/gtm/health-snapshot (mit Auth)",
    });
  }

  return NextResponse.json({
    ok: true,
    fired,
    generated_at: snapshot.generated_at,
    findings,
    counts: { critical: critical.length, warning: warning.length },
    summary_de,
    health_tiles: snapshot.health.tiles.map((t) => ({ id: t.id, status: t.status })),
  });
}
