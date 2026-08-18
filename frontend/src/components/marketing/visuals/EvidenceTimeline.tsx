import React from "react";

import { EVIDENCE_TIMELINE, type EvidenceEvent } from "@/lib/marketing/demoData";

import {
  IconCheck,
  IconDocument,
  IconEvidence,
  IconMapping,
  IconShield,
} from "../ui/Icons";

const KIND_META: Record<
  EvidenceEvent["kind"],
  { label: string; Icon: typeof IconCheck; className: string }
> = {
  upload: {
    label: "Upload",
    Icon: IconDocument,
    className: "border-[var(--mk-slate-200)] bg-[var(--mk-slate-100)] text-[var(--mk-slate-600)]",
  },
  review: {
    label: "Review",
    Icon: IconEvidence,
    className: "border-[var(--mk-warn-100)] bg-[var(--mk-warn-50)] text-[var(--mk-warn-700)]",
  },
  approval: {
    label: "Freigabe",
    Icon: IconCheck,
    className: "border-[var(--mk-ok-100)] bg-[var(--mk-ok-50)] text-[var(--mk-ok-700)]",
  },
  mapping: {
    label: "Mapping",
    Icon: IconMapping,
    className: "border-[var(--mk-accent-100)] bg-[var(--mk-accent-50)] text-[var(--mk-accent-700)]",
  },
  export: {
    label: "Export",
    Icon: IconShield,
    className: "border-[var(--mk-accent-100)] bg-[var(--mk-accent-50)] text-[var(--mk-accent-700)]",
  },
};

/**
 * Audit Trail als Zeitachse: jede Zeile nennt Zeitpunkt, handelnde Person,
 * betroffenes Control und die Art der Änderung.
 */
export function EvidenceTimeline({ className = "" }: { className?: string }) {
  return (
    <div className={`mk-card overflow-hidden ${className}`.trim()}>
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--mk-bd)] bg-[var(--mk-panel-subtle)] px-4 py-2.5">
        <p className="mk-label">Audit Trail · Evidence Engine</p>
        <p className="mk-mono text-[var(--mk-fg-faint)]">append-only</p>
      </div>

      <ol className="relative px-4 py-4">
        <span
          aria-hidden
          className="absolute bottom-6 left-[1.55rem] top-6 w-px bg-[var(--mk-bd)]"
        />
        {EVIDENCE_TIMELINE.map((event) => {
          const meta = KIND_META[event.kind];
          return (
            <li
              key={`${event.date}-${event.title}`}
              className="relative grid grid-cols-[1.5rem_minmax(0,1fr)] gap-3 py-2.5"
            >
              <span
                className={`z-10 flex h-6 w-6 items-center justify-center rounded-full border ${meta.className}`}
              >
                <meta.Icon className="h-3.5 w-3.5" />
              </span>
              <div className="min-w-0">
                <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                  <span className="mk-num text-[0.6875rem] font-semibold text-[var(--mk-fg-faint)]">
                    {event.date}
                  </span>
                  <span className="text-[0.8125rem] font-semibold text-[var(--mk-fg)]">
                    {event.title}
                  </span>
                </div>
                <p className="mt-0.5 text-[0.75rem] leading-relaxed text-[var(--mk-fg-muted)]">
                  {event.detail}
                </p>
                <p className="mt-0.5 text-[0.6875rem] text-[var(--mk-fg-faint)]">
                  {event.actor} · {event.actorRole} · {meta.label}
                </p>
              </div>
            </li>
          );
        })}
      </ol>

      <p className="border-t border-[var(--mk-bd)] bg-[var(--mk-panel-subtle)] px-4 py-2.5 text-[0.6875rem] leading-relaxed text-[var(--mk-fg-faint)]">
        Einträge werden ergänzt, nicht überschrieben. Vorversionen bleiben referenzierbar.
      </p>
    </div>
  );
}
