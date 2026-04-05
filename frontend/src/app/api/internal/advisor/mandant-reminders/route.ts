import { NextResponse } from "next/server";

import {
  createAdvisorMandantReminderManual,
  listAdvisorMandantReminders,
  updateAdvisorMandantReminderStatus,
} from "@/lib/advisorMandantReminderStore";
import type { MandantReminderCategory, MandantReminderStatus } from "@/lib/advisorMandantReminderTypes";
import { MANDANT_REMINDER_MANUAL_CATEGORIES } from "@/lib/advisorMandantReminderTypes";
import { isLeadAdminAuthorized } from "@/lib/leadAdminAuth";

export const runtime = "nodejs";

const CLIENT_ID_RE = /^[a-zA-Z0-9._-]{1,255}$/;

function normalizeDueAtIso(input: string): string {
  const t = input.trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(t)) {
    return new Date(`${t}T23:59:59`).toISOString();
  }
  const ms = Date.parse(t);
  if (Number.isNaN(ms)) throw new Error("invalid_due_at");
  return new Date(ms).toISOString();
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
  const status = url.searchParams.get("status")?.trim() as MandantReminderStatus | undefined;

  const reminders = await listAdvisorMandantReminders({
    tenant_id: clientId || undefined,
    status:
      status === "open" || status === "done" || status === "dismissed" ? status : undefined,
  });

  return NextResponse.json({ ok: true, reminders });
}

type PostBody = {
  client_id?: string;
  category?: string;
  note?: string | null;
  due_at?: string;
};

export async function POST(req: Request) {
  if (!process.env.LEAD_ADMIN_SECRET?.trim()) {
    return NextResponse.json({ error: "not_configured" }, { status: 404 });
  }
  if (!isLeadAdminAuthorized(req)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  let body: PostBody = {};
  try {
    body = (await req.json()) as PostBody;
  } catch {
    return NextResponse.json({ error: "invalid_json" }, { status: 400 });
  }

  const clientId = typeof body.client_id === "string" ? body.client_id.trim() : "";
  if (!clientId || !CLIENT_ID_RE.test(clientId)) {
    return NextResponse.json(
      { error: "invalid_client_id", detail: "client_id required (alphanumeric, dot, underscore, hyphen)." },
      { status: 400 },
    );
  }

  const cat = body.category as MandantReminderCategory | undefined;
  if (!cat || !MANDANT_REMINDER_MANUAL_CATEGORIES.includes(cat)) {
    return NextResponse.json(
      { error: "invalid_category", detail: "category must be manual or follow_up_note." },
      { status: 400 },
    );
  }

  const dueRaw = typeof body.due_at === "string" ? body.due_at : "";
  if (!dueRaw.trim()) {
    return NextResponse.json({ error: "due_at_required" }, { status: 400 });
  }

  let dueAt: string;
  try {
    dueAt = normalizeDueAtIso(dueRaw);
  } catch {
    return NextResponse.json({ error: "invalid_due_at" }, { status: 400 });
  }

  const note =
    body.note === undefined || body.note === null ? null : String(body.note);

  if (cat === "follow_up_note" && !note?.trim()) {
    return NextResponse.json(
      { error: "note_required", detail: "follow_up_note requires a short note." },
      { status: 400 },
    );
  }

  try {
    const reminder = await createAdvisorMandantReminderManual({
      tenant_id: clientId,
      category: cat,
      note,
      due_at: dueAt,
    });
    return NextResponse.json({ ok: true, reminder });
  } catch (e) {
    const msg = e instanceof Error ? e.message : "error";
    if (msg === "invalid_manual_category") {
      return NextResponse.json({ error: "invalid_category" }, { status: 400 });
    }
    return NextResponse.json({ error: "server_error" }, { status: 500 });
  }
}

type PatchBody = {
  reminder_id?: string;
  status?: string;
};

export async function PATCH(req: Request) {
  if (!process.env.LEAD_ADMIN_SECRET?.trim()) {
    return NextResponse.json({ error: "not_configured" }, { status: 404 });
  }
  if (!isLeadAdminAuthorized(req)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  let body: PatchBody = {};
  try {
    body = (await req.json()) as PatchBody;
  } catch {
    return NextResponse.json({ error: "invalid_json" }, { status: 400 });
  }

  const id = typeof body.reminder_id === "string" ? body.reminder_id.trim() : "";
  if (!id) {
    return NextResponse.json({ error: "reminder_id_required" }, { status: 400 });
  }

  const st = body.status;
  if (st !== "done" && st !== "dismissed") {
    return NextResponse.json({ error: "invalid_status" }, { status: 400 });
  }

  const updated = await updateAdvisorMandantReminderStatus(id, st);
  if (!updated) {
    return NextResponse.json({ error: "not_found_or_not_open" }, { status: 404 });
  }

  return NextResponse.json({ ok: true, reminder: updated });
}
