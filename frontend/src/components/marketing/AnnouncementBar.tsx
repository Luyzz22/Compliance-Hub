import Link from "next/link";
import React from "react";

import { MARKETING_ROUTES } from "@/lib/marketing/navigation";

import { IconArrowRight } from "./ui/Icons";

/** Sachliche Ankündigungsleiste — Einordnung statt Alarm. */
export function AnnouncementBar() {
  return (
    <div className="mk-announce">
      <div className="mk-container flex min-h-9 flex-wrap items-center justify-center gap-x-3 gap-y-1 py-1.5 text-center">
        <p className="text-[0.75rem] leading-snug text-[#c3cede]">
          EU AI Act Readiness, NIS2 und ISO 42001 in einem Governance-System.
        </p>
        <Link
          href={MARKETING_ROUTES.aiAct}
          prefetch={false}
          className="group inline-flex items-center gap-1 text-[0.75rem] font-semibold text-white no-underline"
        >
          Vorgehen ansehen
          <IconArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5" />
        </Link>
      </div>
    </div>
  );
}
