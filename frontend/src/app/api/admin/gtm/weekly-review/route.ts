import { NextResponse } from "next/server";

import {
  readGtmWeeklyReviewState,
  sliceRecentNotes,
  updateGtmWeeklyReviewState,
} from "@/lib/gtmWeeklyReviewStore";
import { isLeadAdminAuthorized } from "@/lib/leadAdminAuth";

export const runtime = "nodejs";

export async function GET(req: Request) {
  if (!process.env.LEAD_ADMIN_SECRET?.trim()) {
    return NextResponse.json({ error: "not_configured" }, { status: 404 });
  }
  if (!isLeadAdminAuthorized(req)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const state = await readGtmWeeklyReviewState();
  return NextResponse.json({
    ok: true,
    last_reviewed_at: state.last_reviewed_at,
    recent_notes: sliceRecentNotes(state, 3),
  });
}

type PostBody = {
  mark_reviewed?: boolean;
  note?: string;
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

  const hasNote = Boolean(body.note?.trim());
  if (!body.mark_reviewed && !hasNote) {
    return NextResponse.json({ error: "validation" }, { status: 400 });
  }

  const next = await updateGtmWeeklyReviewState({
    mark_reviewed: Boolean(body.mark_reviewed),
    note: body.note,
  });

  return NextResponse.json({
    ok: true,
    last_reviewed_at: next.last_reviewed_at,
    recent_notes: sliceRecentNotes(next, 3),
  });
}
