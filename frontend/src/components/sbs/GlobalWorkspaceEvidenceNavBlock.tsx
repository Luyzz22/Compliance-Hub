"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import React from "react";

import { useAiActEvidenceNav } from "@/hooks/useAiActEvidenceNav";
import { useWorkspaceTenantIdClient } from "@/hooks/useWorkspaceTenantIdClient";

/**
 * Workspace-Dropdown: Abschnitt „Compliance / Evidence“ nur bei Feature + OPA (tenant-meta).
 */
export function GlobalWorkspaceEvidenceNavBlock() {
  const pathname = usePathname();
  const tid = useWorkspaceTenantIdClient();
  const { visible, href, loading } = useAiActEvidenceNav(tid);

  if (loading || !visible) {
    return null;
  }

  const active = pathname === href || pathname.startsWith(`${href}/`);

  return (
    <>
      <div className="border-t border-slate-100 px-3 py-2 text-[0.65rem] font-bold uppercase tracking-wider text-slate-400">
        Compliance / Evidence
      </div>
      <Link
        href={href}
        role="menuitem"
        className={`block px-3 py-2 text-sm no-underline ${
          active
            ? "bg-cyan-50 font-semibold text-cyan-900"
            : "text-slate-700 hover:bg-slate-50"
        }`}
      >
        EU AI Act Evidenz
      </Link>
    </>
  );
}
