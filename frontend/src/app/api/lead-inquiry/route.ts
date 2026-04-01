import { NextResponse } from "next/server";

import {
  isLeadSegment,
  LEAD_FIELD_LIMITS,
  type LeadInquiryPayload,
} from "@/lib/leadCapture";

type Incoming = {
  name?: string;
  work_email?: string;
  company?: string;
  segment?: string;
  message?: string;
  source_page?: string;
  /** Honeypot – Bots füllen oft versteckte Felder */
  company_website?: string;
};

function trimStr(v: unknown, max: number): string {
  if (typeof v !== "string") return "";
  return v.trim().slice(0, max);
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Öffentlicher Lead-Endpunkt (ohne Auth).
 * Produktion: optional `LEAD_INBOUND_WEBHOOK_URL` für CRM/Slack; sonst strukturierte Logs.
 */
export async function POST(req: Request) {
  let body: Incoming;
  try {
    body = (await req.json()) as Incoming;
  } catch {
    return NextResponse.json({ ok: false, error: "invalid_json" }, { status: 400 });
  }

  if (body.company_website && String(body.company_website).trim() !== "") {
    return NextResponse.json({ ok: true });
  }

  const name = trimStr(body.name, LEAD_FIELD_LIMITS.name);
  const work_email = trimStr(body.work_email, LEAD_FIELD_LIMITS.email).toLowerCase();
  const company = trimStr(body.company, LEAD_FIELD_LIMITS.company);
  const message = trimStr(body.message ?? "", LEAD_FIELD_LIMITS.message);
  const source_page = trimStr(body.source_page, LEAD_FIELD_LIMITS.source_page);

  if (!name || !work_email || !company || !source_page) {
    return NextResponse.json({ ok: false, error: "validation" }, { status: 400 });
  }

  if (!EMAIL_RE.test(work_email)) {
    return NextResponse.json({ ok: false, error: "validation" }, { status: 400 });
  }

  const segRaw = typeof body.segment === "string" ? body.segment.trim() : "";
  if (!isLeadSegment(segRaw)) {
    return NextResponse.json({ ok: false, error: "validation" }, { status: 400 });
  }

  const payload: LeadInquiryPayload = {
    name,
    work_email,
    company,
    segment: segRaw,
    message,
    source_page,
  };

  const webhook = process.env.LEAD_INBOUND_WEBHOOK_URL?.trim();
  if (webhook) {
    try {
      const r = await fetch(webhook, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...payload,
          received_at: new Date().toISOString(),
        }),
      });
      if (!r.ok) {
        console.warn("[lead-inquiry] webhook_non_ok", r.status);
      }
    } catch (e) {
      console.warn("[lead-inquiry] webhook_error", e);
    }
  }

  console.info(
    "[lead-inquiry]",
    JSON.stringify({
      ...payload,
      received_at: new Date().toISOString(),
    }),
  );

  return NextResponse.json({ ok: true });
}
