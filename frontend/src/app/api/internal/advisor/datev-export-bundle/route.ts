import { NextResponse } from "next/server";

import { zipDatevKanzleiBundle, buildDatevKanzleiBundleFiles } from "@/lib/datevKanzleiBundleGenerate";
import { fetchTenantBoardReadinessRaw } from "@/lib/fetchTenantBoardReadinessRaw";
import { isLeadAdminAuthorized } from "@/lib/leadAdminAuth";
import { readGtmProductAccountMap } from "@/lib/gtmProductAccountMapStore";
import { generateMandantReadinessAdvisorExport } from "@/lib/mandantReadinessAdvisorExport";
import { computeMandantOffenePunkte } from "@/lib/tenantBoardReadinessGaps";

export const runtime = "nodejs";

const CLIENT_ID_RE = /^[a-zA-Z0-9._-]{1,255}$/;

function safeZipBaseName(clientId: string): string {
  return clientId.replace(/[^a-zA-Z0-9._-]/g, "_").slice(0, 200) || "mandant";
}

export async function GET(req: Request) {
  if (!process.env.LEAD_ADMIN_SECRET?.trim()) {
    return NextResponse.json({ error: "not_configured" }, { status: 404 });
  }
  if (!isLeadAdminAuthorized(req)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const url = new URL(req.url);
  const clientId = url.searchParams.get("client_id")?.trim() ?? "";
  if (!clientId || !CLIENT_ID_RE.test(clientId)) {
    return NextResponse.json(
      { error: "invalid_client_id", detail: "client_id required (alphanumeric, dot, underscore, hyphen)." },
      { status: 400 },
    );
  }

  const [raw, map] = await Promise.all([
    fetchTenantBoardReadinessRaw(clientId),
    readGtmProductAccountMap(),
  ]);
  const entry = map.entries.find((e) => e.tenant_id === clientId);
  const mandantenBezeichnung = entry?.label?.trim() || clientId;
  const pilotFlag = entry?.pilot === true;

  const nowMs = Date.now();
  const exportPayload = generateMandantReadinessAdvisorExport({
    mandantId: clientId,
    mandantenBezeichnung,
    raw,
    pilotFlag,
    nowMs,
  });
  const punkte = computeMandantOffenePunkte(clientId, raw, nowMs);

  const files = buildDatevKanzleiBundleFiles({
    mandantReadinessMarkdownDe: exportPayload.markdown_de,
    mandantId: clientId,
    raw,
    punkte,
    nowMs,
    exportPayloadVersion: exportPayload.version,
    generatedAtIso: exportPayload.meta.generated_at,
  });

  const zipBuffer = await zipDatevKanzleiBundle(files);
  const day = exportPayload.meta.generated_at.slice(0, 10);
  const filename = `datev-kanzlei-bundle-${safeZipBaseName(clientId)}-${day}.zip`;

  return new NextResponse(new Uint8Array(zipBuffer), {
    status: 200,
    headers: {
      "Content-Type": "application/zip",
      "Content-Disposition": `attachment; filename="${filename}"`,
      "Cache-Control": "no-store",
    },
  });
}
