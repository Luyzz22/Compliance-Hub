import type { PoolClient } from "pg";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  mutateAdvisorMandantRemindersPostgres,
  readAdvisorMandantHistoryPostgres,
  recordAdvisorReviewMarkedPostgres,
  resolveAdvisorRuntimeRetentionDays,
} from "@/lib/advisorRuntimePostgresStore";
import { __setRuntimePostgresPoolFactoryForTests } from "@/lib/runtimePostgres";

type QueryCall = { text: string; values?: unknown[] };

function installDatabase(
  rowsForQuery: (text: string) => unknown[] = () => [],
): QueryCall[] {
  vi.stubEnv("NODE_ENV", "test");
  vi.stubEnv("AZURE_POSTGRES_HOST", "compliancehub.postgres.database.azure.com");
  vi.stubEnv("AZURE_POSTGRES_DATABASE", "compliancehub");
  vi.stubEnv("AZURE_POSTGRES_USER", "runtime-principal");
  vi.stubEnv("COMPLIANCEHUB_RUNTIME_STORAGE_AUTH", "default");
  const calls: QueryCall[] = [];
  const client = {
    async query(text: string, values?: unknown[]) {
      calls.push({ text, values });
      return { rows: rowsForQuery(text) };
    },
    release: vi.fn(),
  } as unknown as PoolClient;
  __setRuntimePostgresPoolFactoryForTests(() => ({
    connect: vi.fn(async () => client),
  }));
  return calls;
}

afterEach(() => {
  __setRuntimePostgresPoolFactoryForTests(null);
  vi.unstubAllEnvs();
});

describe("advisor PostgreSQL persistence", () => {
  it("requires an explicit bounded retention period in production", () => {
    expect(resolveAdvisorRuntimeRetentionDays({ NODE_ENV: "development" })).toBe(1_095);
    expect(() => resolveAdvisorRuntimeRetentionDays({ NODE_ENV: "production" })).toThrow(
      "is required",
    );
    expect(
      resolveAdvisorRuntimeRetentionDays({
        NODE_ENV: "production",
        COMPLIANCEHUB_ADVISOR_RUNTIME_RETENTION_DAYS: "730",
      }),
    ).toBe(730);
    expect(() =>
      resolveAdvisorRuntimeRetentionDays({
        COMPLIANCEHUB_ADVISOR_RUNTIME_RETENTION_DAYS: "10",
      }),
    ).toThrow("between 30 and 3650");
  });

  it("reads a history row inside tenant context and normalizes timestamps", async () => {
    const calls = installDatabase((text) =>
      text.includes("FROM compliancehub_private.advisor_mandant_history")
        ? [
            {
              tenant_id: "tenant-a",
              last_mandant_readiness_export_at: new Date("2026-07-15T10:00:00Z"),
              last_datev_bundle_export_at: null,
              last_review_marked_at: new Date("2026-07-15T11:00:00Z"),
              last_review_note_de: "reviewed",
            },
          ]
        : [],
    );

    await expect(readAdvisorMandantHistoryPostgres("tenant-a")).resolves.toEqual({
      tenant_id: "tenant-a",
      last_mandant_readiness_export_at: "2026-07-15T10:00:00.000Z",
      last_datev_bundle_export_at: null,
      last_review_marked_at: "2026-07-15T11:00:00.000Z",
      last_review_note_de: "reviewed",
    });
    expect(calls.find((call) => call.text.includes("WHERE tenant_id = $1"))?.values).toEqual([
      "tenant-a",
    ]);
    expect(calls.find((call) => call.text.includes("platform_access"))?.values).toEqual([
      "false",
    ]);
  });

  it("upserts review state with bounded notes and optimistic row versioning", async () => {
    const calls = installDatabase();
    await recordAdvisorReviewMarkedPostgres(
      "tenant-a",
      "x".repeat(700),
      "2026-07-15T12:00:00.000Z",
    );

    const upsert = calls.find((call) =>
      call.text.includes("INSERT INTO compliancehub_private.advisor_mandant_history"),
    );
    expect(upsert?.text).toContain("ON CONFLICT (tenant_id) DO UPDATE");
    expect(upsert?.text).toContain("row_version + 1");
    expect((upsert?.values?.[2] as string).length).toBe(500);
    expect(upsert?.values?.[3]).toBe(true);
    expect(upsert?.values?.[4]).toBe(1_095);
  });

  it("serializes reminder mutations and persists only changed domain rows", async () => {
    const calls = installDatabase();
    const created = {
      reminder_id: "3db45f20-b584-4f67-88f0-f891805cc77a",
      tenant_id: "tenant-a",
      category: "manual" as const,
      due_at: "2026-07-20T12:00:00.000Z",
      status: "open" as const,
      note: "follow up",
      source: "manual" as const,
      created_at: "2026-07-15T12:00:00.000Z",
      updated_at: "2026-07-15T12:00:00.000Z",
    };

    const result = await mutateAdvisorMandantRemindersPostgres((state) => {
      state.reminders.push(created);
      return created;
    });

    expect(result).toEqual(created);
    expect(calls.some((call) => call.text.includes("pg_advisory_xact_lock"))).toBe(true);
    const upsert = calls.find((call) =>
      call.text.includes("INSERT INTO compliancehub_private.advisor_mandant_reminders"),
    );
    expect(upsert?.values?.slice(0, 7)).toEqual([
      created.reminder_id,
      created.tenant_id,
      created.category,
      created.due_at,
      created.status,
      created.note,
      created.source,
    ]);
    expect(upsert?.values?.[9]).toBe(1_095);
  });
});
