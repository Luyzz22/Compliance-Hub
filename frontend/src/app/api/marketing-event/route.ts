import { NextResponse } from "next/server";

import {
  InvalidJsonBodyError,
  readBoundedJsonBody,
  RequestBodyTooLargeError,
} from "@/lib/boundedJsonBody";

const MAX_REQUEST_BYTES = 16 * 1024;

type Body = {
  event?: string;
  cta_id?: string;
  quelle?: string;
  t?: number;
  /** z. B. forwarded | stored | stored_forward_failed (keine PII) */
  delivery?: string;
};

/**
 * Minimal internal observability (structured log line).
 * Keine PII; nur Event-Namen und optionale Quell-Marker.
 */
export async function POST(req: Request) {
  let parsed: Body;
  try {
    parsed = await readBoundedJsonBody<Body>(req, MAX_REQUEST_BYTES);
  } catch (error) {
    if (error instanceof RequestBodyTooLargeError) {
      return NextResponse.json({ ok: false }, { status: 413 });
    }
    if (!(error instanceof InvalidJsonBodyError)) throw error;
    return NextResponse.json({ ok: false }, { status: 400 });
  }

  const event = typeof parsed.event === "string" ? parsed.event.trim() : "";
  if (!event || event.length > 64) {
    return NextResponse.json({ ok: false }, { status: 400 });
  }

  const ctaId =
    typeof parsed.cta_id === "string" ? parsed.cta_id.slice(0, 120) : undefined;
  const quelle =
    typeof parsed.quelle === "string" ? parsed.quelle.slice(0, 120) : undefined;
  const delivery =
    typeof parsed.delivery === "string" ? parsed.delivery.slice(0, 48) : undefined;

  console.info(
    "[marketing-event]",
    JSON.stringify({
      event,
      cta_id: ctaId,
      quelle,
      delivery,
      t: typeof parsed.t === "number" ? parsed.t : Date.now(),
    }),
  );

  return NextResponse.json({ ok: true });
}
