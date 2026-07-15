import Link from "next/link";
import React from "react";

import { BRAND_TAGLINE } from "@/lib/appNavConfig";

import { AppSecondaryNav } from "./AppSecondaryNav";
import { GlobalAppNav } from "./GlobalAppNav";

type SbsHeaderProps = {
  publicSite?: boolean;
};

export function SbsHeader({ publicSite = false }: SbsHeaderProps) {
  return (
    <header className="sticky top-0 z-50 border-b border-white/70 bg-white/80 shadow-[0_1px_0_rgba(7,17,31,0.06)] backdrop-blur-2xl backdrop-saturate-150">
      <div className="mx-auto flex min-h-16 max-w-[90rem] items-center justify-between gap-4 px-4 py-2 md:px-8 md:py-2.5">
        <Link href="/" className="group flex min-w-0 flex-1 items-center gap-3 no-underline">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[0.7rem] bg-[#07111f] text-white shadow-lg shadow-slate-950/15" aria-hidden>
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none">
              <path d="M12 3.5a8.5 8.5 0 1 0 0 17" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
              <path d="M13 8h6M13 12h7M13 16h5" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
            </svg>
          </span>
          <span className="min-w-0 leading-tight">
            <span className="block truncate text-sm font-semibold tracking-[-0.02em] text-[#07111f] md:text-base">
              Compliance Hub
            </span>
            <span className="hidden text-[0.65rem] font-medium text-slate-500 sm:block">
              {BRAND_TAGLINE}
            </span>
          </span>
        </Link>
        <GlobalAppNav publicSite={publicSite} />
      </div>
      {!publicSite ? <AppSecondaryNav /> : null}
    </header>
  );
}
