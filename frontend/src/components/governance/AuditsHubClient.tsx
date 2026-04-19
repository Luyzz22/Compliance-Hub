"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { createAuditCase, fetchAuditCases, type GovernanceAuditCaseRow } from "@/lib/auditReadinessApi";
import { CH_BTN_PRIMARY, CH_BTN_SECONDARY, CH_CARD, CH_SECTION_LABEL } from "@/lib/boardLayout";

const DEFAULT_FW = "NIS2,ISO_27001";

interface Props {
  tenantId: string;
}

export function AuditsHubClient({ tenantId }: Props) {
  const [rows, setRows] = useState<GovernanceAuditCaseRow[]>([]);
  const [title, setTitle] = useState("");
  const [fw, setFw] = useState(DEFAULT_FW);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setError(null);
    try {
      setRows(await fetchAuditCases(tenantId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Laden fehlgeschlagen");
    }
  }, [tenantId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function onCreate() {
    if (!title.trim()) {
      setError("Titel eingeben.");
      return;
    }
    setError(null);
    const tags = fw
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    try {
      const created = await createAuditCase(tenantId, {
        title: title.trim(),
        framework_tags: tags,
        control_ids: null,
      });
      window.location.href = `/tenant/governance/audits/${created.id}`;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Anlegen fehlgeschlagen");
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-8 px-4 py-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Governance</p>
        <h1 className="mt-1 text-2xl font-semibold text-slate-900">Audit Readiness</h1>
        <p className="mt-2 text-sm text-slate-600">
          Fälle bündeln Frameworks und Controls; Readiness und Evidence-Gaps werden aus dem
          Unified Control Layer berechnet.
        </p>
      </div>

      {error ? (
        <p className="text-sm text-rose-800" role="alert">
          {error}
        </p>
      ) : null}

      <article className={CH_CARD}>
        <p className={CH_SECTION_LABEL}>Neuer Audit-Fall</p>
        <label className="mt-3 block text-sm font-medium text-slate-700">
          Titel
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            placeholder="z. B. ISO-27001-Überprüfung Q2"
          />
        </label>
        <label className="mt-3 block text-sm font-medium text-slate-700">
          Framework-Tags (Komma)
          <input
            value={fw}
            onChange={(e) => setFw(e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 font-mono text-sm"
          />
        </label>
        <div className="mt-4 flex gap-2">
          <button type="button" onClick={() => void onCreate()} className={CH_BTN_PRIMARY}>
            Anlegen und öffnen
          </button>
          <button type="button" onClick={() => void reload()} className={CH_BTN_SECONDARY}>
            Aktualisieren
          </button>
        </div>
      </article>

      <article className={CH_CARD}>
        <p className={CH_SECTION_LABEL}>Bestehende Fälle</p>
        <ul className="mt-4 divide-y divide-slate-100">
          {rows.length === 0 ? (
            <li className="py-4 text-sm text-slate-600">Noch keine Audit-Fälle.</li>
          ) : (
            rows.map((r) => (
              <li key={r.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                <div>
                  <p className="font-medium text-slate-900">{r.title}</p>
                  <p className="text-xs text-slate-500">
                    {(r.framework_tags ?? []).join(" · ")} · {r.control_ids?.length ?? 0} Controls
                  </p>
                </div>
                <Link
                  href={`/tenant/governance/audits/${r.id}`}
                  className="text-sm font-semibold text-[var(--sbs-navy-mid)] no-underline hover:underline"
                >
                  Öffnen
                </Link>
              </li>
            ))
          )}
        </ul>
      </article>
    </div>
  );
}
