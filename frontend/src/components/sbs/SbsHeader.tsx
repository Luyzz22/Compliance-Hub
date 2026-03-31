import Link from "next/link";
import React from "react";

import { BRAND_TAGLINE } from "@/lib/appNavConfig";

import { AppSecondaryNav } from "./AppSecondaryNav";
import { GlobalAppNav } from "./GlobalAppNav";

export function SbsHeader() {
  return (
    <header className="sticky top-0 z-50 border-b border-slate-200/90 bg-white/95 shadow-sm backdrop-blur-md backdrop-saturate-150 supports-[backdrop-filter]:bg-white/85">
      <div className="mx-auto flex min-h-16 max-w-7xl items-center justify-between gap-4 px-4 py-2 md:px-6 md:py-2.5">
        <Link href="/" className="group flex min-w-0 flex-1 items-center gap-3 no-underline">
          <span
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500 to-teal-600 text-xs font-bold text-white shadow-sm shadow-cyan-900/10"
            aria-hidden
          >
            CH
          </span>
          <span className="min-w-0 leading-tight">
            <span className="block truncate text-sm font-semibold tracking-tight text-slate-900 md:text-base">
              Compliance Hub
            </span>
            <span className="hidden text-[0.65rem] font-medium text-slate-500 sm:block">
              {BRAND_TAGLINE}
            </span>
          </span>
        </Link>
        <GlobalAppNav />
      </div>
      <AppSecondaryNav />
    </header>
  );
}
