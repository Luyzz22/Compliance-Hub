"use client";

import Link from "next/link";
import React from "react";

import { EvidenceAttachmentsSection } from "@/components/evidence/EvidenceAttachmentsSection";
import type { AIGovernanceActionRead } from "@/lib/api";
import { CH_CARD } from "@/lib/boardLayout";

export function GovernanceActionsTableWithEvidence({
  actions,
}: {
  actions: AIGovernanceActionRead[];
}) {
  return (
    <div className={`${CH_CARD} overflow-hidden p-0`}>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50/90 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
              <th className="px-5 py-3">Titel</th>
              <th className="px-5 py-3">Requirement</th>
              <th className="px-5 py-3">Status</th>
              <th className="px-5 py-3">Fällig</th>
              <th className="px-5 py-3">Owner</th>
              <th className="px-5 py-3 text-right">Aktion</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {actions.map((a) => (
              <React.Fragment key={a.id}>
                <tr className="transition hover:bg-slate-50/80">
                  <td className="px-5 py-4 font-semibold text-slate-900">{a.title}</td>
                  <td className="px-5 py-4 text-slate-600">{a.related_requirement}</td>
                  <td className="px-5 py-4">
                    <span className="inline-flex rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-800 ring-1 ring-slate-200/80">
                      {a.status}
                    </span>
                  </td>
                  <td className="px-5 py-4 tabular-nums text-slate-600">
                    {a.due_date
                      ? new Date(a.due_date).toLocaleDateString("de-DE")
                      : "–"}
                  </td>
                  <td className="px-5 py-4 text-slate-600">{a.owner ?? "–"}</td>
                  <td className="px-5 py-4 text-right">
                    <div className="flex flex-wrap justify-end gap-2">
                      {a.related_ai_system_id ? (
                        <Link
                          href={`/tenant/ai-systems/${encodeURIComponent(a.related_ai_system_id)}`}
                          className="text-xs font-semibold text-cyan-700 underline decoration-cyan-700/30 hover:text-cyan-900"
                        >
                          System
                        </Link>
                      ) : null}
                      <Link
                        href="/tenant/eu-ai-act"
                        className="text-xs font-semibold text-cyan-700 underline decoration-cyan-700/30 hover:text-cyan-900"
                      >
                        Bearbeiten
                      </Link>
                    </div>
                  </td>
                </tr>
                <tr className="bg-slate-50/40">
                  <td colSpan={6} className="px-5 py-3">
                    <EvidenceAttachmentsSection
                      compact
                      title="Anhänge zu dieser Maßnahme"
                      description="DPIA, SOPs, Schulungsnachweise oder Verträge als Prüfungsbeleg – mandantenisoliert gespeichert."
                      actionId={a.id}
                    />
                  </td>
                </tr>
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
