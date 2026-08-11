import React from "react";

import { DemoWorkspaceBadge } from "@/components/demo/DemoWorkspaceBadge";
import { ResponsiveTenantNav } from "@/components/sbs/ResponsiveTenantNav";
import { TenantWorkspaceShell } from "@/components/workspace/TenantWorkspaceShell";

export default async function TenantsTenantLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ tenantId: string }>;
}) {
  const { tenantId: raw } = await params;
  const tenantId = decodeURIComponent(raw);

  return (
    <div className="flex w-full min-w-0 flex-col gap-0 lg:flex-row lg:items-start">
      <aside className="w-full shrink-0 border-b border-slate-200 bg-white lg:sticky lg:top-28 lg:max-h-[calc(100vh-8rem)] lg:w-72 lg:self-start lg:overflow-y-auto lg:border-b-0 lg:border-r lg:border-slate-200">
        <div className="border-b border-slate-200 px-4 py-4 md:px-5 md:py-5">
          <div className="text-xs font-semibold text-slate-400">
            Compliance Hub
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-slate-700">
            <span>
              Mandant{" "}
              <span className="font-semibold text-slate-900">{tenantId}</span>
            </span>
            <DemoWorkspaceBadge tenantId={tenantId} />
          </div>
          <p className="mt-2 text-xs leading-relaxed text-slate-500">
            Workspace für Register, Policies, Evidenzen und operative Umsetzung.
          </p>
        </div>
        <ResponsiveTenantNav workspaceTenantId={tenantId} />
      </aside>
      <div className="min-w-0 flex-1 bg-slate-50/90 px-4 py-8 md:px-6 md:py-10">
        <TenantWorkspaceShell tenantId={tenantId}>{children}</TenantWorkspaceShell>
      </div>
    </div>
  );
}
