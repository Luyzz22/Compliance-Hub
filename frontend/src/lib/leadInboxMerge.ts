import {
  deriveLeadAccountKeyFromStoredRecord,
  deriveLeadContactKeyFromStoredRecord,
} from "@/lib/leadIdentity";
import type { LeadContactHistoryEntry, LeadInboxItem, LeadForwardingStatus } from "@/lib/leadInboxTypes";
import type { LeadAdminRow } from "@/lib/leadPersistence";
import type { LeadOpsFile } from "@/lib/leadOpsTypes";
import { getOpsEntryForLead } from "@/lib/leadOpsSelectors";

function forwardingStatus(r: LeadAdminRow): LeadForwardingStatus {
  if (r.webhook_ok === true) return "ok";
  if (r.webhook_ok === false) return "failed";
  return "not_sent";
}

function rowNeedsAttention(r: LeadAdminRow, ops: LeadOpsFile): boolean {
  const o = getOpsEntryForLead(ops, r.lead_id);
  const fw = forwardingStatus(r);
  return fw === "failed" || o.triage_status === "received";
}

export function mergeLeadsWithOps(rows: LeadAdminRow[], ops: LeadOpsFile): LeadInboxItem[] {
  return rows.map((r) => {
    const o = getOpsEntryForLead(ops, r.lead_id);
    const fw = forwardingStatus(r);
    const needs_attention = rowNeedsAttention(r, ops);
    const ob = r.outbound;
    const lead_contact_key = deriveLeadContactKeyFromStoredRecord(r);
    const lead_account_key = deriveLeadAccountKeyFromStoredRecord(r);
    const contact_inquiry_sequence =
      r.contact_inquiry_sequence ?? ob.contact_inquiry_sequence ?? 0;
    const contact_first_seen_at =
      r.contact_first_seen_at ?? ob.contact_first_seen_at ?? r.created_at;
    const contact_latest_seen_at =
      r.contact_latest_seen_at ?? ob.contact_latest_seen_at ?? r.created_at;
    const duplicate_hint = r.duplicate_hint ?? ob.duplicate_hint ?? "none";
    return {
      lead_id: r.lead_id,
      trace_id: r.trace_id,
      pipeline_status: r.status,
      forwarding_status: fw,
      triage_status: o.triage_status,
      owner: o.owner,
      internal_note: o.internal_note,
      created_at: r.created_at,
      segment: ob.segment,
      route_key: ob.route.route_key,
      queue_label: ob.route.queue_label,
      priority: ob.route.priority,
      sla_bucket: ob.route.sla_bucket,
      source_page: ob.source_page,
      company: ob.company,
      business_email: ob.business_email,
      name: ob.name,
      message_preview: ob.message.slice(0, 280),
      message: ob.message,
      webhook_ok: r.webhook_ok,
      webhook_at: r.webhook_at,
      webhook_error: r.webhook_error,
      needs_attention,
      activities: o.activities,
      lead_contact_key,
      lead_account_key,
      contact_inquiry_sequence,
      contact_first_seen_at,
      contact_latest_seen_at,
      duplicate_hint,
      contact_submission_count: 0,
      contact_has_unresolved_repeat: false,
      other_contacts_on_same_account: 0,
      manual_related_lead_ids: o.manual_related_lead_ids,
      duplicate_review: o.duplicate_review,
    };
  });
}

/**
 * Rollups über den gesamten Store: Anzahl Submissions pro Kontakt, offene Dubletten, Account-Überlappung.
 */
export function attachContactRollups(
  items: LeadInboxItem[],
  allRows: LeadAdminRow[],
  ops: LeadOpsFile,
): LeadInboxItem[] {
  const byContact = new Map<string, LeadAdminRow[]>();
  const accountToContacts = new Map<string, Set<string>>();

  for (const r of allRows) {
    const ct = deriveLeadContactKeyFromStoredRecord(r);
    const list = byContact.get(ct) ?? [];
    list.push(r);
    byContact.set(ct, list);
    const ac = deriveLeadAccountKeyFromStoredRecord(r);
    if (ac) {
      const set = accountToContacts.get(ac) ?? new Set<string>();
      set.add(ct);
      accountToContacts.set(ac, set);
    }
  }

  for (const [, group] of byContact) {
    group.sort(
      (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    );
  }

  const sequenceByLeadId = new Map<string, number>();
  for (const [, group] of byContact) {
    group.forEach((row, idx) => {
      sequenceByLeadId.set(row.lead_id, idx + 1);
    });
  }

  const rollupUnresolved = new Map<string, boolean>();
  for (const [ct, group] of byContact) {
    const any = group.some((row) => rowNeedsAttention(row, ops));
    rollupUnresolved.set(ct, any);
  }

  return items.map((item) => {
    const group = byContact.get(item.lead_contact_key) ?? [];
    const count = group.length;
    const seqStored = item.contact_inquiry_sequence > 0;
    const seq = seqStored ? item.contact_inquiry_sequence : (sequenceByLeadId.get(item.lead_id) ?? 1);
    const unresolvedRepeat =
      count > 1 && (rollupUnresolved.get(item.lead_contact_key) ?? false);
    let otherOnAccount = 0;
    if (item.lead_account_key) {
      const set = accountToContacts.get(item.lead_account_key);
      if (set) {
        otherOnAccount = Math.max(0, set.size - 1);
      }
    }
    return {
      ...item,
      contact_inquiry_sequence: seq,
      contact_submission_count: count,
      contact_has_unresolved_repeat: unresolvedRepeat,
      other_contacts_on_same_account: otherOnAccount,
    };
  });
}

export function sortInboxItems(items: LeadInboxItem[]): LeadInboxItem[] {
  return [...items].sort((a, b) => {
    const na = a.needs_attention ? 0 : 1;
    const nb = b.needs_attention ? 0 : 1;
    if (na !== nb) return na - nb;
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });
}

export function buildContactHistoryItems(
  focusLeadId: string,
  allRows: LeadAdminRow[],
  ops: LeadOpsFile,
): LeadContactHistoryEntry[] {
  const focus = allRows.find((r) => r.lead_id === focusLeadId);
  if (!focus) return [];
  const ct = deriveLeadContactKeyFromStoredRecord(focus);
  const group = allRows
    .filter((r) => deriveLeadContactKeyFromStoredRecord(r) === ct)
    .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());

  const sequenceByLeadId = new Map<string, number>();
  group.forEach((row, idx) => sequenceByLeadId.set(row.lead_id, idx + 1));

  return group.map((r) => {
    const o = getOpsEntryForLead(ops, r.lead_id);
    const fw = forwardingStatus(r);
    const ob = r.outbound;
    return {
      lead_id: r.lead_id,
      trace_id: r.trace_id,
      created_at: r.created_at,
      pipeline_status: r.status,
      forwarding_status: fw,
      triage_status: o.triage_status,
      owner: o.owner,
      internal_note: o.internal_note,
      source_page: ob.source_page,
      segment: ob.segment,
      message_preview: ob.message.slice(0, 200),
      contact_inquiry_sequence:
        r.contact_inquiry_sequence ?? ob.contact_inquiry_sequence ?? sequenceByLeadId.get(r.lead_id) ?? 1,
      duplicate_hint: r.duplicate_hint ?? ob.duplicate_hint ?? "none",
      duplicate_review: o.duplicate_review,
      needs_attention: rowNeedsAttention(r, ops),
    };
  });
}
