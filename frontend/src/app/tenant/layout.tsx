import React from "react";

import { TenantNav } from "@/components/sbs/TenantNav";

export default function TenantLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="relative ml-[calc(-50vw+50%)] w-screen max-w-[100vw] shrink-0">
      <div className="sbs-tenant-shell">
        <aside className="sbs-tenant-sidebar">
          <div className="border-b border-slate-200 px-5 py-5">
            <div className="text-[0.65rem] font-bold uppercase tracking-[0.12em] text-slate-400">
              Compliance Hub
            </div>
            <div className="mt-1 text-sm text-slate-700">
              Mandant{" "}
              <span className="font-semibold text-slate-900">tenant-overview-001</span>
            </div>
            <p className="mt-2 text-xs leading-relaxed text-slate-500">
              Tenant-Cockpit für Register, Policies und Nachweise.
            </p>
          </div>
          <TenantNav />
        </aside>
        <div className="sbs-tenant-main min-w-0">{children}</div>
      </div>
    </div>
  );
}
