import React from "react";

import { DemoWorkspaceBadge } from "@/components/demo/DemoWorkspaceBadge";
import { TenantNav } from "@/components/sbs/TenantNav";
import { TenantWorkspaceShell } from "@/components/workspace/TenantWorkspaceShell";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

export default async function TenantsTenantLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ tenantId: string }>;
}) {
  const { tenantId: raw } = await params;
  const tenantId = decodeURIComponent(raw);
  const workspaceId = await getWorkspaceTenantIdServer();
  const mismatch = workspaceId !== tenantId;

  return (
    <div className="flex w-full min-w-0 flex-col gap-0 lg:flex-row lg:items-start">
      <aside className="w-full shrink-0 border-b border-slate-200 bg-white lg:w-60 lg:border-b-0 lg:border-r lg:border-slate-200">
        <div className="border-b border-slate-200 px-4 py-4 md:px-5 md:py-5">
          <div className="text-[0.65rem] font-bold uppercase tracking-[0.12em] text-slate-400">
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
        <TenantNav workspaceTenantId={tenantId} />
      </aside>
      <div className="min-w-0 flex-1 bg-slate-50/90 px-4 py-8 md:px-6 md:py-10">
        <TenantWorkspaceShell tenantId={tenantId}>
          {mismatch ? (
            <div
              className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
              role="status"
            >
              Hinweis: Die Mandanten-ID in der URL ({tenantId}) weicht vom aktiven Workspace (
              {workspaceId}) ab. API-Aufrufe auf dieser Seite verwenden die URL-ID.
            </div>
          ) : null}
          {children}
        </TenantWorkspaceShell>
      </div>
    </div>
  );
}
