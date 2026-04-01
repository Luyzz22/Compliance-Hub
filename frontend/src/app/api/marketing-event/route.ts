import { NextResponse } from "next/server";

type Body = {
  event?: string;
  cta_id?: string;
  quelle?: string;
  t?: number;
};

/**
 * Minimal internal observability (structured log line).
 * Keine PII; nur Event-Namen und optionale Quell-Marker.
 */
export async function POST(req: Request) {
  let parsed: Body;
  try {
    parsed = (await req.json()) as Body;
  } catch {
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

  console.info(
    "[marketing-event]",
    JSON.stringify({
      event,
      cta_id: ctaId,
      quelle,
      t: typeof parsed.t === "number" ? parsed.t : Date.now(),
    }),
  );

  return NextResponse.json({ ok: true });
}
