import Link from "next/link";
import React from "react";

import { CH_BTN_SECONDARY, CH_PAGE_NAV_LINK } from "@/lib/boardLayout";

/**
 * Konsistente Sprünge vom Board in den Tenant-Workspace (ohne API-Logik).
 */
export function BoardToWorkspaceCtas() {
  return (
    <div className="mt-4 flex flex-wrap items-center gap-2 rounded-xl border border-slate-200/80 bg-slate-50/80 px-4 py-3">
      <span className="text-[0.65rem] font-semibold uppercase tracking-wide text-slate-500">
        Workspace
      </span>
      <Link href="/tenant/ai-systems" className={`${CH_BTN_SECONDARY} py-2 text-xs`}>
        KI-Systeme
      </Link>
      <Link
        href="/tenant/compliance-overview"
        className={`${CH_BTN_SECONDARY} py-2 text-xs`}
      >
        Mandanten-Übersicht
      </Link>
      <Link href="/tenant/policies" className={`${CH_BTN_SECONDARY} py-2 text-xs`}>
        Policies
      </Link>
      <Link
        href="/board/eu-ai-act-readiness"
        className={CH_PAGE_NAV_LINK + " ml-auto text-xs"}
      >
        Board: EU AI Act Readiness
      </Link>
    </div>
  );
}
