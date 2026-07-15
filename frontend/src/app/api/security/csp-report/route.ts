import { NextResponse } from "next/server";

import {
  CSP_REPORT_MAX_BYTES,
  sanitizeCspReports,
} from "@/lib/cspReport";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const ACCEPTED_MEDIA_TYPES = new Set([
  "application/csp-report",
  "application/reports+json",
]);

function emptyResponse(status: number): Response {
  return new Response(null, {
    status,
    headers: {
      "Cache-Control": "private, no-store",
    },
  });
}

async function readBoundedBody(request: Request): Promise<string | null> {
  if (!request.body) return "";
  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let totalBytes = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      totalBytes += value.byteLength;
      if (totalBytes > CSP_REPORT_MAX_BYTES) {
        await reader.cancel();
        return null;
      }
      chunks.push(value);
    }
    const body = new Uint8Array(totalBytes);
    let offset = 0;
    for (const chunk of chunks) {
      body.set(chunk, offset);
      offset += chunk.byteLength;
    }
    return new TextDecoder("utf-8", { fatal: true }).decode(body);
  } finally {
    reader.releaseLock();
  }
}

export async function POST(request: Request): Promise<Response> {
  const mediaType = request.headers.get("content-type")?.split(";", 1)[0].trim().toLowerCase();
  if (!mediaType || !ACCEPTED_MEDIA_TYPES.has(mediaType)) return emptyResponse(415);

  const contentLength = Number(request.headers.get("content-length"));
  if (Number.isFinite(contentLength) && contentLength > CSP_REPORT_MAX_BYTES) {
    return emptyResponse(413);
  }

  let body: string | null;
  try {
    body = await readBoundedBody(request);
  } catch {
    return emptyResponse(400);
  }
  if (body === null) return emptyResponse(413);

  let payload: unknown;
  try {
    payload = JSON.parse(body) as unknown;
  } catch {
    return emptyResponse(400);
  }

  const reports = sanitizeCspReports(payload);
  if (reports.length === 0) return emptyResponse(400);

  for (const report of reports) {
    console.warn("[security.csp_violation]", JSON.stringify(report));
  }
  return emptyResponse(204);
}

export function GET(): NextResponse {
  return NextResponse.json(
    { error: "method_not_allowed" },
    {
      status: 405,
      headers: {
        Allow: "POST",
        "Cache-Control": "private, no-store",
      },
    },
  );
}
