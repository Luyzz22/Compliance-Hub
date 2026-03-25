import React from "react";

import { TenantNav } from "@/components/sbs/TenantNav";

export default function TenantLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex w-full min-w-0 flex-col gap-0 lg:flex-row lg:items-start">
      <aside className="w-full shrink-0 border-b border-slate-200 bg-white lg:w-60 lg:border-b-0 lg:border-r lg:border-slate-200">
        <div className="border-b border-slate-200 px-4 py-4 md:px-5 md:py-5">
          <div className="text-[0.65rem] font-bold uppercase tracking-[0.12em] text-slate-400">
            Compliance Hub
          </div>
          <div className="mt-1 text-sm text-slate-700">
            Mandant{" "}
            <span className="font-semibold text-slate-900">tenant-overview-001</span>
          </div>
          <p className="mt-2 text-xs leading-relaxed text-slate-500">
            Workspace für Register, Policies, Evidenzen und operative Umsetzung.
          </p>
        </div>
        <TenantNav />
      </aside>
      <div className="min-w-0 flex-1 bg-slate-50/90 px-4 py-8 md:px-6 md:py-10">
        {children}
      </div>
    </div>
  );
}
