import { randomUUID } from "crypto";
import { NextResponse } from "next/server";

import { validateBusinessEmailDomain, validateFormTiming } from "@/lib/leadAntiAbuse";
import {
  checkLeadEmailCooldown,
  rollbackLeadEmailCooldown,
} from "@/lib/leadDuplicateGuard";
import { isLeadSegment, LEAD_FIELD_LIMITS } from "@/lib/leadCapture";
import {
  buildLeadAccountKey,
  buildLeadContactKey,
  normalizeLeadEmail,
} from "@/lib/leadIdentity";
import { buildLeadOutboundPayload } from "@/lib/leadOutbound";
import {
  appendLeadWebhookResult,
  computeContactKeyStatsFromRows,
  countOtherContactKeysOnAccount,
  dispatchLeadWebhook,
  persistLeadReceived,
  readAllLeadRecordsMerged,
  type LeadStoreRecord,
} from "@/lib/leadPersistence";
import { appendLeadOpsActivity } from "@/lib/leadOpsState";
import { getClientIp, checkLeadIpRateLimit } from "@/lib/leadRateLimit";
import { determineLeadRoute } from "@/lib/leadRouting";

export const runtime = "nodejs";

type Incoming = {
  name?: string;
  work_email?: string;
  company?: string;
  segment?: string;
  message?: string;
  source_page?: string;
  company_website?: string;
  /** ms seit Epoch – Formular geöffnet (Client) */
  form_opened_at?: number;
};

function trimStr(v: unknown, max: number): string {
  if (typeof v !== "string") return "";
  return v.trim().slice(0, max);
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export async function POST(req: Request) {
  const clientIp = getClientIp(req);
  const rl = checkLeadIpRateLimit(clientIp);
  if (!rl.ok) {
    console.warn("[lead-inquiry] rate_limited_ip", clientIp.slice(0, 20));
    return NextResponse.json(
      {
        ok: false,
        error: "rate_limited",
        retry_after_sec: rl.retry_after_sec,
      },
      { status: 429 },
    );
  }

  let body: Incoming;
  try {
    body = (await req.json()) as Incoming;
  } catch {
    return NextResponse.json({ ok: false, error: "invalid_json" }, { status: 400 });
  }

  if (body.company_website && String(body.company_website).trim() !== "") {
    return NextResponse.json({ ok: true, honeypot: true });
  }

  const timing = validateFormTiming(
    typeof body.form_opened_at === "number" ? body.form_opened_at : undefined,
  );
  if (!timing.ok) {
    console.warn("[lead-inquiry] timing_reject", { clientIp: clientIp.slice(0, 20) });
    return NextResponse.json({ ok: false, error: "too_fast" }, { status: 400 });
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

  const requireBiz = process.env.LEAD_REQUIRE_BUSINESS_EMAIL === "1";
  const biz = validateBusinessEmailDomain(work_email, requireBiz);
  if (!biz.ok) {
    return NextResponse.json({ ok: false, error: "business_email_required" }, { status: 400 });
  }

  const dup = checkLeadEmailCooldown(work_email);
  if (!dup.ok) {
    return NextResponse.json(
      {
        ok: false,
        error: "duplicate_cooldown",
        retry_after_sec: dup.retry_after_sec,
      },
      { status: 429 },
    );
  }

  const segRaw = typeof body.segment === "string" ? body.segment.trim() : "";
  if (!isLeadSegment(segRaw)) {
    return NextResponse.json({ ok: false, error: "validation" }, { status: 400 });
  }

  const lead_id = randomUUID();
  const trace_id = randomUUID();
  const route = determineLeadRoute(segRaw, company, message, source_page);

  const normEmail = normalizeLeadEmail(work_email);
  const lead_contact_key = buildLeadContactKey(normEmail);
  const lead_account_key = buildLeadAccountKey(company, work_email);

  const allRows = await readAllLeadRecordsMerged();
  const contactStats = computeContactKeyStatsFromRows(allRows, lead_contact_key);
  const sequence = contactStats.prior_count + 1;
  const created_at = new Date().toISOString();
  const contact_first_seen_at = contactStats.first_seen_at ?? created_at;
  const contact_latest_seen_at = created_at;
  const duplicate_hint = sequence > 1 ? ("same_email_repeat" as const) : ("none" as const);

  const otherContactsOnAccount = countOtherContactKeysOnAccount(
    allRows,
    lead_account_key,
    lead_contact_key,
  );

  const outbound = buildLeadOutboundPayload({
    lead_id,
    trace_id,
    source_page,
    segment: segRaw,
    name,
    work_email,
    company,
    message,
    route,
    timestamp: created_at,
    identity: {
      lead_contact_key,
      lead_account_key,
      contact_inquiry_sequence: sequence,
      contact_first_seen_at,
      contact_latest_seen_at,
      duplicate_hint,
    },
  });

  const storeRecord: LeadStoreRecord = {
    _kind: "lead_inquiry",
    lead_id,
    trace_id,
    status: "received",
    created_at,
    outbound,
    lead_contact_key,
    lead_account_key,
    contact_inquiry_sequence: sequence,
    contact_first_seen_at,
    contact_latest_seen_at,
    duplicate_hint,
  };

  try {
    await persistLeadReceived(storeRecord);
  } catch (e) {
    rollbackLeadEmailCooldown(work_email);
    console.error("[lead-inquiry] persist_error", e);
    return NextResponse.json({ ok: false, error: "server" }, { status: 500 });
  }

  try {
    if (sequence > 1) {
      await appendLeadOpsActivity(
        lead_id,
        "contact_repeat_detected",
        `Wiederholte Anfrage (#${sequence}) für denselben Kontakt-Schlüssel`,
      );
    }
    if (otherContactsOnAccount > 0) {
      await appendLeadOpsActivity(
        lead_id,
        "possible_duplicate_noted",
        `Account-Gruppe: ${otherContactsOnAccount} weiterer Kontext (anderer E-Mail-Kontakt)`,
      );
    }
  } catch (e) {
    console.warn("[lead-inquiry] ops_activity_append_failed", e);
  }

  console.info(
    "[lead-inquiry]",
    JSON.stringify({
      lead_id,
      trace_id,
      segment: segRaw,
      route_key: route.route_key,
      source_page,
      lead_contact_key,
      contact_inquiry_sequence: sequence,
      client_ip_prefix: clientIp.slice(0, 12),
    }),
  );

  const webhook = process.env.LEAD_INBOUND_WEBHOOK_URL?.trim();
  let delivery: "forwarded" | "stored" | "stored_forward_failed" = "stored";
  let delivery_note_de: string | undefined;

  if (webhook) {
    const wh = await dispatchLeadWebhook(webhook, outbound, 3);
    const at = new Date().toISOString();
    if (wh.ok) {
      delivery = "forwarded";
      await appendLeadWebhookResult({
        _kind: "webhook_result",
        lead_id,
        trace_id,
        ok: true,
        at,
      });
      console.info("[lead-webhook]", JSON.stringify({ trace_id, lead_id, ok: true }));
    } else {
      delivery = "stored_forward_failed";
      delivery_note_de =
        "Ihre Anfrage ist bei uns eingegangen. Die automatische Weiterleitung ist vorübergehend fehlgeschlagen – wir bearbeiten die Anfrage dennoch manuell.";
      await appendLeadWebhookResult({
        _kind: "webhook_result",
        lead_id,
        trace_id,
        ok: false,
        at,
        error: wh.error,
      });
      console.warn("[lead-webhook]", JSON.stringify({ trace_id, lead_id, ok: false, err: wh.error }));
    }
  }

  return NextResponse.json({
    ok: true,
    lead_id,
    trace_id,
    delivery,
    ...(delivery_note_de ? { delivery_note_de } : {}),
  });
}
