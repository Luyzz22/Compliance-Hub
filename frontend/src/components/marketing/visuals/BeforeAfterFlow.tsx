import React from "react";

import { IconAlert, IconCheck } from "../ui/Icons";

type FlowNode = {
  title: string;
  detail: string;
  /** Bruchstelle im Ablauf (nur „Vorher“). */
  breakAfter?: string;
};

const BEFORE: FlowNode[] = [
  {
    title: "Excel-Listen",
    detail: "Systeme, Risiken und Controls in getrennten Dateien",
    breakAfter: "Kein gemeinsamer Stand",
  },
  {
    title: "E-Mail-Abstimmung",
    detail: "Zuständigkeit und Freigabe im Postfach",
    breakAfter: "Entscheidung nicht belegbar",
  },
  {
    title: "Berater-Workstreams",
    detail: "Je Regelwerk ein eigenes Projekt und Format",
    breakAfter: "Doppelte Erhebung",
  },
  {
    title: "SharePoint-Ordner",
    detail: "Nachweise ohne Versions- und Review-Bezug",
    breakAfter: "Suche statt Vorlage",
  },
  {
    title: "Board-Präsentation",
    detail: "Manuell zusammengestellt, Stand vom Vortag",
  },
];

const AFTER: FlowNode[] = [
  {
    title: "Inventar",
    detail: "KI-Systeme, Assets, Anbieter und Prozesse mit Owner",
  },
  {
    title: "Control Mapping",
    detail: "Ein Control, mehrere Regelwerke — versioniert",
  },
  {
    title: "Evidence",
    detail: "Nachweis mit Herkunft, Version und Review-Zyklus",
  },
  {
    title: "Risiko & Maßnahmen",
    detail: "Bewertet, priorisiert, mit Frist und Verantwortung",
  },
  {
    title: "Board Report",
    detail: "Lage, Entscheidungsbedarf und Fristen auf Abruf",
  },
];

function Connector({ tone, note }: { tone: "before" | "after"; note?: string }) {
  return (
    <li
      aria-hidden
      className="flex shrink-0 items-center justify-center lg:w-[4.75rem] lg:flex-col lg:justify-start lg:pt-7"
    >
      <span className="flex h-8 w-8 rotate-90 items-center justify-center lg:h-auto lg:w-auto lg:rotate-0">
        <svg
          viewBox="0 0 24 12"
          width="24"
          height="12"
          className={
            tone === "before"
              ? "text-[var(--mk-warn-500)]"
              : "text-[var(--mk-accent-500)]"
          }
        >
          <path
            d="M1 6h18"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinecap="round"
            strokeDasharray={tone === "before" ? "3 3" : undefined}
          />
          <path
            d="m17 2.5 4.5 3.5L17 9.5"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
      {note ? (
        <span className="hidden px-1 text-center text-[0.5625rem] leading-[1.25] text-[var(--mk-warn-700)] lg:mt-2 lg:block">
          {note}
        </span>
      ) : null}
    </li>
  );
}

function FlowRow({
  tone,
  label,
  caption,
  nodes,
}: {
  tone: "before" | "after";
  label: string;
  caption: string;
  nodes: FlowNode[];
}) {
  const isBefore = tone === "before";
  return (
    <div
      className={`rounded-[14px] border p-4 sm:p-5 ${
        isBefore
          ? "border-[var(--mk-warn-100)] bg-[var(--mk-warn-50)]"
          : "border-[var(--mk-accent-100)] bg-[var(--mk-accent-50)]"
      }`}
    >
      <div className="flex items-start gap-2.5">
        {isBefore ? (
          <IconAlert className="mt-0.5 h-4 w-4 shrink-0 text-[var(--mk-warn-600)]" />
        ) : (
          <IconCheck className="mt-0.5 h-4 w-4 shrink-0 text-[var(--mk-accent-600)]" />
        )}
        <div>
          <p
            className={`text-[0.6875rem] font-bold uppercase tracking-[0.12em] ${
              isBefore ? "text-[var(--mk-warn-700)]" : "text-[var(--mk-accent-700)]"
            }`}
          >
            {label}
          </p>
          <p className="mt-1 text-[0.8125rem] leading-relaxed text-[var(--mk-fg-soft)]">
            {caption}
          </p>
        </div>
      </div>

      <ol className="mt-4 flex flex-col lg:flex-row lg:items-stretch">
        {nodes.map((node, index) => (
          <React.Fragment key={node.title}>
            <li className="min-w-0 flex-1">
              <div
                className={`h-full rounded-[10px] border bg-white p-3 ${
                  isBefore ? "border-[var(--mk-warn-100)]" : "border-[var(--mk-accent-100)]"
                }`}
              >
                <p className="mk-mono text-[var(--mk-fg-faint)]">
                  {String(index + 1).padStart(2, "0")}
                </p>
                <p className="mt-1 text-[0.8125rem] font-semibold text-[var(--mk-fg)]">
                  {node.title}
                </p>
                <p className="mt-1.5 text-[0.6875rem] leading-relaxed text-[var(--mk-fg-muted)]">
                  {node.detail}
                </p>
              </div>
            </li>
            {index < nodes.length - 1 ? (
              <Connector tone={tone} note={node.breakAfter} />
            ) : null}
          </React.Fragment>
        ))}
      </ol>
    </div>
  );
}

/**
 * Vorher/Nachher als Ablaufdiagramm — jede Station ist fachlich benannt,
 * Bruchstellen werden im „Vorher“-Pfad ausgewiesen statt bebildert.
 */
export function BeforeAfterFlow() {
  return (
    <div className="grid gap-4">
      <FlowRow
        tone="before"
        label="Vorher"
        caption="Fünf Werkzeuge, vier Übergaben — und kein gemeinsamer Stand, auf den sich die Geschäftsleitung berufen kann."
        nodes={BEFORE}
      />
      <FlowRow
        tone="after"
        label="Nachher"
        caption="Ein durchgehender Ablauf: Was einmal erfasst ist, trägt Mapping, Nachweis, Maßnahme und Bericht."
        nodes={AFTER}
      />
    </div>
  );
}
