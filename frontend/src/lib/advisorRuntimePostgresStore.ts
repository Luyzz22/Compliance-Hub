import "server-only";

import type { PoolClient } from "pg";

import type {
  AdvisorMandantHistoryEntry,
  AdvisorMandantHistoryState,
} from "@/lib/advisorMandantHistoryTypes";
import type {
  AdvisorMandantRemindersState,
  MandantReminderRecord,
  MandantReminderStatus,
} from "@/lib/advisorMandantReminderTypes";
import {
  RuntimePostgresConfigurationError,
  withPlatformRuntimePostgres,
  withTenantRuntimePostgres,
} from "@/lib/runtimePostgres";

const HISTORY_ACTOR = "frontend:advisor-history";
const REMINDER_ACTOR = "frontend:advisor-reminders";
const DEFAULT_ADVISOR_RETENTION_DAYS = 1_095;
type RuntimeEnvironment = Readonly<Record<string, string | undefined>>;

type DatabaseTimestamp = string | Date;

type HistoryRow = {
  tenant_id: string;
  last_mandant_readiness_export_at: DatabaseTimestamp | null;
  last_datev_bundle_export_at: DatabaseTimestamp | null;
  last_review_marked_at: DatabaseTimestamp | null;
  last_review_note_de: string | null;
};

type ReminderRow = {
  reminder_id: string;
  tenant_id: string;
  category: MandantReminderRecord["category"];
  due_at: DatabaseTimestamp;
  status: MandantReminderRecord["status"];
  note: string | null;
  source: MandantReminderRecord["source"];
  created_at: DatabaseTimestamp;
  updated_at: DatabaseTimestamp;
};

export function resolveAdvisorRuntimeRetentionDays(
  env: RuntimeEnvironment = process.env,
): number {
  const configured = env.COMPLIANCEHUB_ADVISOR_RUNTIME_RETENTION_DAYS?.trim();
  if (!configured) {
    if (env.NODE_ENV === "production" || env.VERCEL) {
      throw new RuntimePostgresConfigurationError(
        "COMPLIANCEHUB_ADVISOR_RUNTIME_RETENTION_DAYS is required in production",
      );
    }
    return DEFAULT_ADVISOR_RETENTION_DAYS;
  }
  if (!/^\d{2,4}$/.test(configured)) {
    throw new RuntimePostgresConfigurationError(
      "Invalid advisor runtime retention period",
    );
  }
  const days = Number(configured);
  if (!Number.isSafeInteger(days) || days < 30 || days > 3_650) {
    throw new RuntimePostgresConfigurationError(
      "Advisor runtime retention period must be between 30 and 3650 days",
    );
  }
  return days;
}

function timestampToIso(value: DatabaseTimestamp | null): string | null {
  if (value === null) return null;
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) {
    throw new RuntimePostgresConfigurationError(
      "Invalid timestamp returned by runtime PostgreSQL",
    );
  }
  return date.toISOString();
}

function requireIsoTimestamp(value: string): string {
  const normalized = value.trim();
  const date = new Date(normalized);
  if (!normalized || Number.isNaN(date.getTime())) {
    throw new RuntimePostgresConfigurationError(
      "Invalid ISO timestamp for runtime PostgreSQL",
    );
  }
  return date.toISOString();
}

function historyFromRow(row: HistoryRow): AdvisorMandantHistoryEntry {
  return {
    tenant_id: row.tenant_id,
    last_mandant_readiness_export_at: timestampToIso(
      row.last_mandant_readiness_export_at,
    ),
    last_datev_bundle_export_at: timestampToIso(row.last_datev_bundle_export_at),
    last_review_marked_at: timestampToIso(row.last_review_marked_at),
    last_review_note_de: row.last_review_note_de,
  };
}

function reminderFromRow(row: ReminderRow): MandantReminderRecord {
  return {
    reminder_id: row.reminder_id,
    tenant_id: row.tenant_id,
    category: row.category,
    due_at: timestampToIso(row.due_at)!,
    status: row.status,
    note: row.note,
    source: row.source,
    created_at: timestampToIso(row.created_at)!,
    updated_at: timestampToIso(row.updated_at)!,
  };
}

const HISTORY_SELECT = `
  SELECT
    tenant_id,
    last_mandant_readiness_export_at,
    last_datev_bundle_export_at,
    last_review_marked_at,
    last_review_note_de
  FROM compliancehub_private.advisor_mandant_history
`;

const REMINDER_SELECT = `
  SELECT
    reminder_id::text AS reminder_id,
    tenant_id,
    category,
    due_at,
    status,
    note,
    source,
    created_at,
    updated_at
  FROM compliancehub_private.advisor_mandant_reminders
`;

export async function readAllAdvisorMandantHistoryPostgres(): Promise<AdvisorMandantHistoryState> {
  return withPlatformRuntimePostgres(HISTORY_ACTOR, async (client) => {
    const result = await client.query<HistoryRow>(
      `${HISTORY_SELECT} ORDER BY tenant_id`,
    );
    return { entries: result.rows.map(historyFromRow) };
  });
}

export async function readAdvisorMandantHistoryPostgres(
  tenantId: string,
): Promise<AdvisorMandantHistoryEntry | null> {
  return withTenantRuntimePostgres(tenantId, HISTORY_ACTOR, async (client) => {
    const result = await client.query<HistoryRow>(
      `${HISTORY_SELECT} WHERE tenant_id = $1`,
      [tenantId.trim()],
    );
    return result.rows[0] ? historyFromRow(result.rows[0]) : null;
  });
}

async function recordHistoryTimestamp(
  tenantId: string,
  atIso: string,
  column:
    | "last_mandant_readiness_export_at"
    | "last_datev_bundle_export_at",
): Promise<void> {
  const timestamp = requireIsoTimestamp(atIso);
  const retentionDays = resolveAdvisorRuntimeRetentionDays();
  await withTenantRuntimePostgres(tenantId, HISTORY_ACTOR, async (client) => {
    await client.query(
      `
        INSERT INTO compliancehub_private.advisor_mandant_history (
          tenant_id,
          ${column},
          retention_until
        ) VALUES ($1, $2::timestamptz, clock_timestamp() + make_interval(days => $3))
        ON CONFLICT (tenant_id) DO UPDATE SET
          ${column} = CASE
            WHEN compliancehub_private.advisor_mandant_history.${column} IS NULL
              OR compliancehub_private.advisor_mandant_history.${column} < EXCLUDED.${column}
            THEN EXCLUDED.${column}
            ELSE compliancehub_private.advisor_mandant_history.${column}
          END,
          retention_until = clock_timestamp() + make_interval(days => $3),
          updated_at = clock_timestamp(),
          row_version = compliancehub_private.advisor_mandant_history.row_version + 1
      `,
      [tenantId.trim(), timestamp, retentionDays],
    );
  });
}

export function recordMandantReadinessExportPostgres(
  tenantId: string,
  atIso: string,
): Promise<void> {
  return recordHistoryTimestamp(
    tenantId,
    atIso,
    "last_mandant_readiness_export_at",
  );
}

export function recordDatevBundleExportPostgres(
  tenantId: string,
  atIso: string,
): Promise<void> {
  return recordHistoryTimestamp(tenantId, atIso, "last_datev_bundle_export_at");
}

export async function recordAdvisorReviewMarkedPostgres(
  tenantId: string,
  noteDe: string | undefined,
  atIso: string,
): Promise<void> {
  const timestamp = requireIsoTimestamp(atIso);
  const note = noteDe?.trim() ? noteDe.trim().slice(0, 500) : null;
  const retentionDays = resolveAdvisorRuntimeRetentionDays();
  await withTenantRuntimePostgres(tenantId, HISTORY_ACTOR, async (client) => {
    await client.query(
      `
        INSERT INTO compliancehub_private.advisor_mandant_history (
          tenant_id,
          last_review_marked_at,
          last_review_note_de,
          retention_until
        ) VALUES (
          $1,
          $2::timestamptz,
          $3,
          clock_timestamp() + make_interval(days => $5)
        )
        ON CONFLICT (tenant_id) DO UPDATE SET
          last_review_marked_at = EXCLUDED.last_review_marked_at,
          last_review_note_de = CASE
            WHEN $4::boolean THEN EXCLUDED.last_review_note_de
            ELSE compliancehub_private.advisor_mandant_history.last_review_note_de
          END,
          retention_until = clock_timestamp() + make_interval(days => $5),
          updated_at = clock_timestamp(),
          row_version = compliancehub_private.advisor_mandant_history.row_version + 1
      `,
      [tenantId.trim(), timestamp, note, noteDe !== undefined, retentionDays],
    );
  });
}

async function selectAllReminders(client: PoolClient): Promise<MandantReminderRecord[]> {
  const result = await client.query<ReminderRow>(
    `${REMINDER_SELECT} ORDER BY due_at, reminder_id`,
  );
  return result.rows.map(reminderFromRow);
}

export async function readAllAdvisorMandantRemindersPostgres(): Promise<AdvisorMandantRemindersState> {
  return withPlatformRuntimePostgres(REMINDER_ACTOR, async (client) => ({
    reminders: await selectAllReminders(client),
  }));
}

export async function listAdvisorMandantRemindersPostgres(filters?: {
  tenant_id?: string;
  status?: MandantReminderStatus;
}): Promise<MandantReminderRecord[]> {
  const tenantId = filters?.tenant_id?.trim();
  const query = async (client: PoolClient) => {
    const conditions: string[] = [];
    const values: string[] = [];
    if (tenantId) {
      values.push(tenantId);
      conditions.push(`tenant_id = $${values.length}`);
    }
    if (filters?.status) {
      values.push(filters.status);
      conditions.push(`status = $${values.length}`);
    }
    const where = conditions.length ? ` WHERE ${conditions.join(" AND ")}` : "";
    const result = await client.query<ReminderRow>(
      `${REMINDER_SELECT}${where} ORDER BY due_at, reminder_id`,
      values,
    );
    return result.rows.map(reminderFromRow);
  };

  return tenantId
    ? withTenantRuntimePostgres(tenantId, REMINDER_ACTOR, query)
    : withPlatformRuntimePostgres(REMINDER_ACTOR, query);
}

function reminderFingerprint(reminder: MandantReminderRecord): string {
  return JSON.stringify(reminder);
}

async function upsertChangedReminders(
  client: PoolClient,
  before: Map<string, string>,
  after: MandantReminderRecord[],
): Promise<void> {
  const retentionDays = resolveAdvisorRuntimeRetentionDays();
  const afterIds = new Set(after.map((reminder) => reminder.reminder_id));
  for (const existingId of before.keys()) {
    if (!afterIds.has(existingId)) {
      throw new Error("Advisor reminder deletion requires the governed deletion workflow");
    }
  }

  for (const reminder of after) {
    if (before.get(reminder.reminder_id) === reminderFingerprint(reminder)) continue;
    await client.query(
      `
        INSERT INTO compliancehub_private.advisor_mandant_reminders (
          reminder_id,
          tenant_id,
          category,
          due_at,
          status,
          note,
          source,
          created_at,
          updated_at,
          retention_until
        ) VALUES (
          $1::uuid,
          $2,
          $3,
          $4::timestamptz,
          $5,
          $6,
          $7,
          $8::timestamptz,
          $9::timestamptz,
          CASE
            WHEN $5 = 'open' THEN NULL
            ELSE $9::timestamptz + make_interval(days => $10)
          END
        )
        ON CONFLICT (reminder_id) DO UPDATE SET
          tenant_id = EXCLUDED.tenant_id,
          category = EXCLUDED.category,
          due_at = EXCLUDED.due_at,
          status = EXCLUDED.status,
          note = EXCLUDED.note,
          source = EXCLUDED.source,
          updated_at = EXCLUDED.updated_at,
          retention_until = CASE
            WHEN EXCLUDED.status = 'open' THEN NULL
            ELSE EXCLUDED.updated_at + make_interval(days => $10)
          END,
          row_version = compliancehub_private.advisor_mandant_reminders.row_version + 1
      `,
      [
        reminder.reminder_id,
        reminder.tenant_id,
        reminder.category,
        requireIsoTimestamp(reminder.due_at),
        reminder.status,
        reminder.note,
        reminder.source,
        requireIsoTimestamp(reminder.created_at),
        requireIsoTimestamp(reminder.updated_at),
        retentionDays,
      ],
    );
  }
}

export async function mutateAdvisorMandantRemindersPostgres<T>(
  operation: (state: AdvisorMandantRemindersState) => Promise<T> | T,
): Promise<T> {
  return withPlatformRuntimePostgres(REMINDER_ACTOR, async (client) => {
    await client.query(
      "SELECT pg_advisory_xact_lock(hashtextextended('compliancehub:advisor-reminders', 0))",
    );
    const reminders = await selectAllReminders(client);
    const before = new Map(
      reminders.map((reminder) => [reminder.reminder_id, reminderFingerprint(reminder)]),
    );
    const state: AdvisorMandantRemindersState = {
      reminders: reminders.map((reminder) => ({ ...reminder })),
    };
    const result = await operation(state);
    await upsertChangedReminders(client, before, state.reminders);
    return result;
  });
}
