"use client";

import React from "react";

import { CH_PAGE_NAV_LINK } from "@/lib/boardLayout";

const SECTIONS = [
  { id: "sec-stammdaten", label: "Stammdaten" },
  { id: "sec-evidenz", label: "Evidenz" },
  { id: "sec-klassifikation", label: "Klassifikation" },
  { id: "sec-nis2", label: "NIS2 / KRITIS" },
  { id: "sec-incidents", label: "Incidents" },
  { id: "sec-compliance", label: "Compliance" },
  { id: "sec-violations", label: "Violations" },
  { id: "sec-massnahmen", label: "Maßnahmen" },
] as const;

/**
 * In-Page-Anker für die KI-System-Detailseite (scroll-mt via Section-IDs).
 */
export function AiSystemSectionNav() {
  return (
    <nav
      className="-mx-1 mb-6 flex flex-wrap gap-1 rounded-xl border border-slate-200/80 bg-slate-50/90 px-3 py-2"
      aria-label="Abschnitte auf dieser Seite"
    >
      {SECTIONS.map((s) => (
        <a key={s.id} href={`#${s.id}`} className={CH_PAGE_NAV_LINK + " px-2 py-1 text-xs"}>
          {s.label}
        </a>
      ))}
    </nav>
  );
}
