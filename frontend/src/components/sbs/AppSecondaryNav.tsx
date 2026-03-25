"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import React from "react";

import { BOARD_NAV_ITEMS, WORKSPACE_NAV_ITEMS } from "@/lib/appNavConfig";

function subLink(active: boolean) {
  return [
    "whitespace-nowrap rounded-md px-2.5 py-1.5 text-xs font-medium transition",
    active
      ? "bg-white text-cyan-900 shadow-sm ring-1 ring-slate-200/80"
      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
  ].join(" ");
}

export function AppSecondaryNav() {
  const pathname = usePathname();

  if (pathname.startsWith("/board")) {
    return (
      <div className="border-t border-slate-200/80 bg-slate-50/95">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-1 px-4 py-2 md:px-6">
          <span className="mr-2 text-[0.65rem] font-bold uppercase tracking-wider text-slate-400">
            Board
          </span>
          {BOARD_NAV_ITEMS.map((item) => {
            const active =
              pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link key={item.href} href={item.href} className={subLink(active)}>
                {item.label}
              </Link>
            );
          })}
          <Link
            href="/tenant/ai-systems"
            className="ml-auto text-xs font-semibold text-cyan-800 underline decoration-cyan-600/30 underline-offset-4 hover:text-cyan-950"
          >
            Zum Workspace
          </Link>
        </div>
      </div>
    );
  }

  if (pathname.startsWith("/tenant")) {
    return (
      <div className="border-t border-slate-200/80 bg-slate-50/95">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-1 px-4 py-2 md:px-6">
          <span className="mr-2 text-[0.65rem] font-bold uppercase tracking-wider text-slate-400">
            Workspace
          </span>
          {WORKSPACE_NAV_ITEMS.map((item) => {
            const active =
              pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link key={item.href} href={item.href} className={subLink(active)}>
                {item.label}
              </Link>
            );
          })}
          <Link
            href="/board/kpis"
            className="ml-auto text-xs font-semibold text-cyan-800 underline decoration-cyan-600/30 underline-offset-4 hover:text-cyan-950"
          >
            Zum Board
          </Link>
        </div>
      </div>
    );
  }

  return null;
}
