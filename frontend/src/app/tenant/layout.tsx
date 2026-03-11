import React from "react";

export default function TenantLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 flex">
      <aside className="w-64 border-r border-slate-800 bg-slate-950/80 backdrop-blur">
        <div className="px-6 py-5 border-b border-slate-800">
          <div className="text-xs font-semibold tracking-widest text-slate-400">
            COMPLIANCE HUB
          </div>
          <div className="mt-1 text-sm text-slate-300">
            Tenant: <span className="font-medium">tenant-overview-001</span>
          </div>
        </div>
        <nav className="px-3 py-4 space-y-1 text-sm">
          <div className="px-2 pb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Overview
          </div>
          <a
            href="/tenant/compliance-overview"
            className="flex items-center gap-2 rounded-md px-2 py-1.5 bg-slate-800 text-slate-50"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            Tenant Compliance
          </a>
          <a
            href="/tenant/eu-ai-act"
            className="flex items-center gap-2 rounded-md px-2 py-1.5 text-slate-400 hover:bg-slate-900 hover:text-slate-50"
          >
            EU AI Act
          </a>
          <a
            href="/tenant/ai-systems"
            className="flex items-center gap-2 rounded-md px-2 py-1.5 text-slate-400 hover:bg-slate-900 hover:text-slate-50"
          >
            AI Systems
          </a>
          <a
            href="/tenant/policies"
            className="flex items-center gap-2 rounded-md px-2 py-1.5 text-slate-400 hover:bg-slate-900 hover:text-slate-50"
          >
            Policies & Rules
          </a>
          <a
            href="/tenant/audit-log"
            className="flex items-center gap-2 rounded-md px-2 py-1.5 text-slate-400 hover:bg-slate-900 hover:text-slate-50"
          >
            Audit Log
          </a>
          <a
            href="/tenant/blueprints"
            className="flex items-center gap-2 rounded-md px-2 py-1.5 text-slate-400 hover:bg-slate-900 hover:text-slate-50"
          >
            Blueprints & Settings
          </a>
        </nav>
      </aside>
      <main className="flex-1 p-8">{children}</main>
    </div>
  );
}
