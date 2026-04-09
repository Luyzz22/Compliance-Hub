"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import React from "react";

import { useAiActEvidenceNav } from "@/hooks/useAiActEvidenceNav";
import { useWorkspaceTenantIdClient } from "@/hooks/useWorkspaceTenantIdClient";
import {
  ADMIN_NAV_ITEMS,
  BOARD_NAV_ITEMS,
  REPORTING_NAV_ITEMS,
  WORKSPACE_NAV_ITEMS,
} from "@/lib/appNavConfig";

function subLink(active: boolean) {
  return [
    "whitespace-nowrap rounded-md px-2.5 py-1.5 text-xs font-medium transition",
    active
      ? "bg-white text-cyan-900 shadow-sm ring-1 ring-slate-200/80"
      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
  ].join(" ");
}

function NavStrip({
  label,
  items,
  pathname,
  crossLink,
}: {
  label: string;
  items: ReadonlyArray<{ href: string; label: string }>;
  pathname: string;
  crossLink?: { href: string; label: string };
}) {
  return (
    <div className="border-t border-slate-200/80 bg-slate-50/95">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-1 px-4 py-2 md:px-6">
        <span className="mr-2 text-[0.65rem] font-bold uppercase tracking-wider text-slate-400">
          {label}
        </span>
        {items.map((item) => {
          const active =
            pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link key={item.href} href={item.href} className={subLink(active)}>
              {item.label}
            </Link>
          );
        })}
        {crossLink ? (
          <Link
            href={crossLink.href}
            className="ml-auto text-xs font-semibold text-cyan-800 underline decoration-cyan-600/30 underline-offset-4 hover:text-cyan-950"
          >
            {crossLink.label}
          </Link>
        ) : null}
      </div>
    </div>
  );
}

export function AppSecondaryNav() {
  const pathname = usePathname();
  const workspaceTenantId = useWorkspaceTenantIdClient();
  const { visible: evidenceVisible, href: evidenceHref, loading: evidenceLoading } =
    useAiActEvidenceNav(workspaceTenantId);
  const evidenceActive =
    pathname === evidenceHref || pathname.startsWith(`${evidenceHref}/`);

  const isReportingPage = REPORTING_NAV_ITEMS.some(
    (r) => pathname === r.href || pathname.startsWith(`${r.href}/`),
  );

  if (isReportingPage) {
    return (
      <NavStrip
        label="Reporting"
        items={REPORTING_NAV_ITEMS}
        pathname={pathname}
        crossLink={{ href: "/board/kpis", label: "Zum Board" }}
      />
    );
  }

  if (pathname.startsWith("/board")) {
    return (
      <NavStrip
        label="Board"
        items={BOARD_NAV_ITEMS}
        pathname={pathname}
        crossLink={{ href: "/tenant/ai-systems", label: "Zum Workspace" }}
      />
    );
  }

  if (pathname.startsWith("/tenant") || pathname.startsWith("/tenants")) {
    const workspaceItems = [
      ...WORKSPACE_NAV_ITEMS,
      ...(!evidenceLoading && evidenceVisible
        ? [{ href: evidenceHref, label: "EU AI Act Evidenz" }]
        : []),
    ];
    return (
      <NavStrip
        label="Workspace"
        items={workspaceItems}
        pathname={pathname}
        crossLink={{ href: "/board/kpis", label: "Zum Board" }}
      />
    );
  }

  if (pathname.startsWith("/admin")) {
    return (
      <NavStrip
        label="Admin"
        items={ADMIN_NAV_ITEMS}
        pathname={pathname}
        crossLink={{ href: "/board/kpis", label: "Zum Board" }}
      />
    );
  }

  return null;
}
