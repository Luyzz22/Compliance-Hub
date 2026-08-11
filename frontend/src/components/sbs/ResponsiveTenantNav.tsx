"use client";

import { useId, useState } from "react";

import { TenantNav } from "@/components/sbs/TenantNav";

type ResponsiveTenantNavProps = {
  workspaceTenantId: string;
};

export function ResponsiveTenantNav({
  workspaceTenantId,
}: ResponsiveTenantNavProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigationId = useId();

  return (
    <>
      <button
        type="button"
        className="flex min-h-11 w-full items-center justify-between gap-3 px-4 py-3 text-left text-sm font-semibold text-slate-800 md:px-5 lg:hidden"
        aria-expanded={mobileOpen}
        aria-controls={navigationId}
        onClick={() => setMobileOpen((current) => !current)}
      >
        Workspace-Bereiche
        <span
          className={`text-slate-500 transition-transform ${mobileOpen ? "rotate-180" : ""}`}
          aria-hidden
        >
          ⌄
        </span>
      </button>
      <div
        id={navigationId}
        className={`${mobileOpen ? "block" : "hidden"} border-t border-slate-200 lg:block lg:border-t-0`}
      >
        <TenantNav workspaceTenantId={workspaceTenantId} />
      </div>
    </>
  );
}
